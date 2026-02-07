import socket
import threading
import json
import sqlite3
import time
import random

class StockTradingServer:
    def __init__(self, host='0.0.0.0', port=10024):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []
        self.stocks = {}
        self.orders = []
        self.connections = []
        self.admin_password = 'admin123'  # 后台管理密码
        self.setup_database()
        self.load_stocks()
        
    def setup_database(self):
        conn = sqlite3.connect('stock_trading.db')
        c = conn.cursor()
        
        # 创建用户表
        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            balance REAL DEFAULT 20000
        )
        ''')
        
        # 创建股票表
        c.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT UNIQUE,
            company_name TEXT,
            price REAL,
            change REAL
        )
        ''')
        
        # 创建持仓表
        c.execute('''
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stock_code TEXT,
            quantity INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # 创建交易记录表
        c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stock_code TEXT,
            type TEXT,
            price REAL,
            quantity INTEGER,
            timestamp TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_stocks(self):
        conn = sqlite3.connect('stock_trading.db')
        c = conn.cursor()
        c.execute('SELECT stock_code, company_name, price, change FROM stocks')
        for row in c.fetchall():
            self.stocks[row[0]] = {
                'company_name': row[1],
                'price': row[2],
                'change': row[3]
            }
        conn.close()
    
    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"服务器启动在 {self.host}:{self.port}")
        
        # 启动市场模拟线程
        market_thread = threading.Thread(target=self.simulate_market)
        market_thread.daemon = True
        market_thread.start()
        
        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"新连接: {client_address}")
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.daemon = True
            client_thread.start()
    
    def handle_client(self, client_socket):
        self.connections.append(client_socket)
        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                try:
                    request = json.loads(data)
                    response = self.process_request(request)
                    client_socket.send(json.dumps(response).encode('utf-8'))
                except json.JSONDecodeError:
                    response = {'error': 'Invalid JSON'}
                    client_socket.send(json.dumps(response).encode('utf-8'))
        except Exception as e:
            print(f"处理客户端请求时出错: {e}")
        finally:
            client_socket.close()
            self.connections.remove(client_socket)
    
    def process_request(self, request):
        action = request.get('action')
        
        if action == 'register':
            return self.register_user(request)
        elif action == 'login':
            return self.login_user(request)
        elif action == 'get_stocks':
            return self.get_stocks()
        elif action == 'get_user_info':
            return self.get_user_info(request)
        elif action == 'buy':
            return self.buy_stock(request)
        elif action == 'sell':
            return self.sell_stock(request)
        elif action == 'add_stock':
            # 验证管理员密码
            if request.get('admin_password') != self.admin_password:
                return {'success': False, 'message': '管理员密码错误'}
            return self.add_stock(request)
        elif action == 'delete_stock':
            # 验证管理员密码
            if request.get('admin_password') != self.admin_password:
                return {'success': False, 'message': '管理员密码错误'}
            return self.delete_stock(request)
        elif action == 'get_users':
            # 验证管理员密码
            if request.get('admin_password') != self.admin_password:
                return {'success': False, 'message': '管理员密码错误'}
            return self.get_users()
        else:
            return {'error': 'Unknown action'}
    
    def register_user(self, request):
        username = request.get('username')
        password = request.get('password')
        
        conn = sqlite3.connect('stock_trading.db')
        c = conn.cursor()
        
        try:
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            return {'success': True, 'message': '注册成功'}
        except sqlite3.IntegrityError:
            return {'success': False, 'message': '用户名已存在'}
        finally:
            conn.close()
    
    def login_user(self, request):
        username = request.get('username')
        password = request.get('password')
        
        conn = sqlite3.connect('stock_trading.db')
        c = conn.cursor()
        c.execute('SELECT id, balance FROM users WHERE username = ? AND password = ?', (username, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            return {'success': True, 'user_id': user[0], 'balance': user[1]}
        else:
            return {'success': False, 'message': '用户名或密码错误'}
    
    def get_stocks(self):
        return {'success': True, 'stocks': self.stocks}
    
    def get_user_info(self, request):
        user_id = request.get('user_id')
        
        conn = sqlite3.connect('stock_trading.db')
        c = conn.cursor()
        
        # 获取用户余额
        c.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
        balance = c.fetchone()[0]
        
        # 获取用户持仓
        c.execute('SELECT stock_code, quantity FROM holdings WHERE user_id = ?', (user_id,))
        holdings = []
        for row in c.fetchall():
            stock_code, quantity = row
            stock_info = self.stocks.get(stock_code, {})
            if stock_info:
                holdings.append({
                    'stock_code': stock_code,
                    'company_name': stock_info['company_name'],
                    'quantity': quantity,
                    'current_price': stock_info['price'],
                    'value': quantity * stock_info['price']
                })
        
        conn.close()
        return {'success': True, 'balance': balance, 'holdings': holdings}
    
    def buy_stock(self, request):
        user_id = request.get('user_id')
        stock_code = request.get('stock_code')
        quantity = request.get('quantity')
        
        if stock_code not in self.stocks:
            return {'success': False, 'message': '股票不存在'}
        
        stock_price = self.stocks[stock_code]['price']
        total_cost = stock_price * quantity
        
        conn = sqlite3.connect('stock_trading.db')
        c = conn.cursor()
        
        # 检查用户余额
        c.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
        balance = c.fetchone()[0]
        
        if balance < total_cost:
            conn.close()
            return {'success': False, 'message': '余额不足'}
        
        # 更新用户余额
        new_balance = balance - total_cost
        c.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, user_id))
        
        # 检查是否已有持仓
        c.execute('SELECT quantity FROM holdings WHERE user_id = ? AND stock_code = ?', (user_id, stock_code))
        existing = c.fetchone()
        
        if existing:
            # 更新持仓
            new_quantity = existing[0] + quantity
            c.execute('UPDATE holdings SET quantity = ? WHERE user_id = ? AND stock_code = ?', 
                     (new_quantity, user_id, stock_code))
        else:
            # 新建持仓
            c.execute('INSERT INTO holdings (user_id, stock_code, quantity) VALUES (?, ?, ?)', 
                     (user_id, stock_code, quantity))
        
        # 记录交易
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        c.execute('INSERT INTO transactions (user_id, stock_code, type, price, quantity, timestamp) VALUES (?, ?, ?, ?, ?, ?)', 
                 (user_id, stock_code, 'buy', stock_price, quantity, timestamp))
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': '购买成功', 'new_balance': new_balance}
    
    def sell_stock(self, request):
        user_id = request.get('user_id')
        stock_code = request.get('stock_code')
        quantity = request.get('quantity')
        
        if stock_code not in self.stocks:
            return {'success': False, 'message': '股票不存在'}
        
        stock_price = self.stocks[stock_code]['price']
        total_revenue = stock_price * quantity
        
        conn = sqlite3.connect('stock_trading.db')
        c = conn.cursor()
        
        # 检查用户持仓
        c.execute('SELECT quantity FROM holdings WHERE user_id = ? AND stock_code = ?', (user_id, stock_code))
        existing = c.fetchone()
        
        if not existing or existing[0] < quantity:
            conn.close()
            return {'success': False, 'message': '持仓不足'}
        
        # 更新用户余额
        c.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
        balance = c.fetchone()[0]
        new_balance = balance + total_revenue
        c.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, user_id))
        
        # 更新持仓
        new_quantity = existing[0] - quantity
        if new_quantity > 0:
            c.execute('UPDATE holdings SET quantity = ? WHERE user_id = ? AND stock_code = ?', 
                     (new_quantity, user_id, stock_code))
        else:
            c.execute('DELETE FROM holdings WHERE user_id = ? AND stock_code = ?', (user_id, stock_code))
        
        # 记录交易
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        c.execute('INSERT INTO transactions (user_id, stock_code, type, price, quantity, timestamp) VALUES (?, ?, ?, ?, ?, ?)', 
                 (user_id, stock_code, 'sell', stock_price, quantity, timestamp))
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': '卖出成功', 'new_balance': new_balance}
    
    def add_stock(self, request):
        stock_code = request.get('stock_code')
        company_name = request.get('company_name')
        price = request.get('price')
        
        conn = sqlite3.connect('stock_trading.db')
        c = conn.cursor()
        
        try:
            c.execute('INSERT INTO stocks (stock_code, company_name, price, change) VALUES (?, ?, ?, ?)', 
                     (stock_code, company_name, price, 0))
            conn.commit()
            self.stocks[stock_code] = {
                'company_name': company_name,
                'price': price,
                'change': 0
            }
            conn.close()
            return {'success': True, 'message': '股票添加成功'}
        except sqlite3.IntegrityError:
            conn.close()
            return {'success': False, 'message': '股票代码已存在'}
    
    def delete_stock(self, request):
        stock_code = request.get('stock_code')
        
        conn = sqlite3.connect('stock_trading.db')
        c = conn.cursor()
        
        # 检查是否有用户持有该股票
        c.execute('SELECT COUNT(*) FROM holdings WHERE stock_code = ?', (stock_code,))
        if c.fetchone()[0] > 0:
            conn.close()
            return {'success': False, 'message': '有用户持有该股票，无法删除'}
        
        c.execute('DELETE FROM stocks WHERE stock_code = ?', (stock_code,))
        if c.rowcount > 0:
            conn.commit()
            if stock_code in self.stocks:
                del self.stocks[stock_code]
            conn.close()
            return {'success': True, 'message': '股票删除成功'}
        else:
            conn.close()
            return {'success': False, 'message': '股票不存在'}
    
    def get_users(self):
        conn = sqlite3.connect('stock_trading.db')
        c = conn.cursor()
        c.execute('SELECT id, username, balance FROM users')
        users = []
        for row in c.fetchall():
            users.append({
                'id': row[0],
                'username': row[1],
                'balance': row[2]
            })
        conn.close()
        return {'success': True, 'users': users}
    
    def simulate_market(self):
        while True:
            # 模拟股票价格波动
            for stock_code in self.stocks:
                change = random.uniform(-0.05, 0.05)  # 价格波动范围 -5% 到 +5%
                old_price = self.stocks[stock_code]['price']
                new_price = old_price * (1 + change)
                new_price = round(new_price, 2)
                
                # 更新股票价格和涨幅
                self.stocks[stock_code]['price'] = new_price
                self.stocks[stock_code]['change'] = round(change * 100, 2)
                
                # 更新数据库
                conn = sqlite3.connect('stock_trading.db')
                c = conn.cursor()
                c.execute('UPDATE stocks SET price = ?, change = ? WHERE stock_code = ?', 
                         (new_price, self.stocks[stock_code]['change'], stock_code))
                conn.commit()
                conn.close()
            
            # 每30秒更新一次
            time.sleep(30)

if __name__ == '__main__':
    server = StockTradingServer()
    server.start()