import socket
import threading
import json
import sqlite3
import time
import random
import signal
import sys

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
        self.generate_html_files()
        
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
    
    def generate_html_files(self):
        """生成Linux端需要的HTML文件"""
        import os
        
        # 创建linux_frontend/templates目录
        templates_dir = os.path.join('..', 'linux_frontend', 'templates')
        if not os.path.exists(templates_dir):
            os.makedirs(templates_dir, exist_ok=True)
        
        # 生成index.html
        index_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>股票交易系统后台</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .nav {
            background-color: #333;
            color: white;
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        .nav a {
            color: white;
            text-decoration: none;
            margin: 0 10px;
            padding: 5px 10px;
            border-radius: 3px;
        }
        .nav a:hover {
            background-color: #555;
        }
        .card {
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .btn {
            display: inline-block;
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 5px;
        }
        .btn:hover {
            background-color: #45a049;
        }
        .btn-danger {
            background-color: #f44336;
        }
        .btn-danger:hover {
            background-color: #da190b;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>股票交易系统后台管理</h1>
        <div class="nav">
            <a href="/">首页</a>
            <a href="/stocks">股票管理</a>
            <a href="/users">用户管理</a>
        </div>
        <div class="card">
            <h2>系统概览</h2>
            <p>欢迎使用股票交易系统后台管理界面。</p>
            <p>在此系统中，您可以：</p>
            <ul>
                <li>添加或删除上市公司</li>
                <li>管理用户账户</li>
                <li>查看市场行情</li>
            </ul>
            <a href="/stocks" class="btn">进入股票管理</a>
            <a href="/users" class="btn">进入用户管理</a>
        </div>
    </div>
</body>
</html>'''
        
        with open(os.path.join(templates_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(index_html)
        
        # 生成stocks.html
        stocks_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>股票管理</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .nav {
            background-color: #333;
            color: white;
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        .nav a {
            color: white;
            text-decoration: none;
            margin: 0 10px;
            padding: 5px 10px;
            border-radius: 3px;
        }
        .nav a:hover {
            background-color: #555;
        }
        .card {
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"], input[type="number"] {
            width: 100%;
            padding: 8px;
            box-sizing: border-box;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .btn {
            display: inline-block;
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 5px;
            border: none;
            cursor: pointer;
        }
        .btn:hover {
            background-color: #45a049;
        }
        .btn-danger {
            background-color: #f44336;
        }
        .btn-danger:hover {
            background-color: #da190b;
        }
        .success {
            color: green;
            margin-top: 10px;
        }
        .error {
            color: red;
            margin-top: 10px;
        }
        .change-positive {
            color: red;
        }
        .change-negative {
            color: green;
        }
    </style>
    <script>
        function addStock() {
            const form = document.getElementById('addStockForm');
            const formData = new FormData(form);
            
            fetch('/add_stock', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                const messageDiv = document.getElementById('message');
                if (data.success) {
                    messageDiv.className = 'success';
                    messageDiv.textContent = data.message;
                    // 刷新页面
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    messageDiv.className = 'error';
                    messageDiv.textContent = data.message;
                }
            });
        }
        
        function deleteStock(stockCode) {
            if (confirm('确定要删除这只股票吗？')) {
                const formData = new FormData();
                formData.append('stock_code', stockCode);
                
                fetch('/delete_stock', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    const messageDiv = document.getElementById('message');
                    if (data.success) {
                        messageDiv.className = 'success';
                        messageDiv.textContent = data.message;
                        // 刷新页面
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000);
                    } else {
                        messageDiv.className = 'error';
                        messageDiv.textContent = data.message;
                    }
                });
            }
        }
    </script>
    <!-- K线图弹窗 -->
    <div id="klineModal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.4);">
        <div style="background-color: #fefefe; margin: 15% auto; padding: 20px; border: 1px solid #888; width: 80%; max-width: 1000px; border-radius: 5px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 id="klineTitle">股票K线图</h3>
                <button onclick="closeKLine()" style="font-size: 20px; cursor: pointer; background: none; border: none;">&times;</button>
            </div>
            <div id="klineContainer" style="width: 100%; height: 400px;"></div>
        </div>
    </div>
    
    <!-- 引入ECharts库 -->
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <script>
        function showKLine(stockCode) {
            document.getElementById('klineTitle').textContent = stockCode + ' 股票K线图';
            document.getElementById('klineModal').style.display = 'block';
            
            // 生成模拟K线数据
            const data = [];
            let basePrice = Math.random() * 100 + 10;
            
            for (let i = 30; i >= 0; i--) {
                const open = basePrice;
                const close = basePrice * (1 + (Math.random() - 0.5) * 0.1);
                const high = Math.max(open, close) * (1 + Math.random() * 0.05);
                const low = Math.min(open, close) * (1 - Math.random() * 0.05);
                basePrice = close;
                
                data.push([
                    new Date(Date.now() - i * 24 * 60 * 60 * 1000).getTime(),
                    open.toFixed(2),
                    high.toFixed(2),
                    low.toFixed(2),
                    close.toFixed(2)
                ]);
            }
            
            // 初始化ECharts实例
            const chartDom = document.getElementById('klineContainer');
            const myChart = echarts.init(chartDom);
            
            const option = {
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                        type: 'cross'
                    }
                },
                legend: {
                    data: ['K线']
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    containLabel: true
                },
                xAxis: {
                    type: 'time',
                    boundaryGap: false
                },
                yAxis: {
                    type: 'value',
                    scale: true
                },
                series: [
                    {
                        name: 'K线',
                        type: 'candlestick',
                        data: data,
                        itemStyle: {
                            color: '#ef232a',
                            color0: '#14b143',
                            borderColor: '#ef232a',
                            borderColor0: '#14b143'
                        }
                    }
                ]
            };
            
            myChart.setOption(option);
            
            // 响应式调整
            window.addEventListener('resize', function() {
                myChart.resize();
            });
        }
        
        function closeKLine() {
            document.getElementById('klineModal').style.display = 'none';
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>股票管理</h1>
        <div class="nav">
            <a href="/">首页</a>
            <a href="/stocks">股票管理</a>
            <a href="/users">用户管理</a>
        </div>
        
        <div class="card">
            <h2>添加新股票</h2>
            <form id="addStockForm" onsubmit="addStock(); return false;">
                <div class="form-group">
                    <label for="stock_code">股票代码</label>
                    <input type="text" id="stock_code" name="stock_code" required>
                </div>
                <div class="form-group">
                    <label for="company_name">公司名称</label>
                    <input type="text" id="company_name" name="company_name" required>
                </div>
                <div class="form-group">
                    <label for="price">初始价格</label>
                    <input type="number" id="price" name="price" step="0.01" min="0.01" required>
                </div>
                <button type="submit" class="btn">添加股票</button>
            </form>
            <div id="message"></div>
        </div>
        
        <div class="card">
            <h2>现有股票</h2>
            <table>
                <tr>
                    <th>股票代码</th>
                    <th>公司名称</th>
                    <th>当前价格</th>
                    <th>涨跌幅</th>
                    <th>操作</th>
                </tr>
                {% for stock_code, stock_info in stocks.items() %}
                <tr>
                    <td>{{ stock_code }}</td>
                    <td>{{ stock_info.company_name }}</td>
                    <td>¥{{ stock_info.price }}</td>
                    <td class="{{ 'change-positive' if stock_info.change > 0 else 'change-negative' }}">
                        {{ '+' if stock_info.change > 0 else '' }}{{ stock_info.change }}%
                    </td>
                    <td>
                        <button class="btn" onclick="showKLine('{{ stock_code }}')">查看K线</button>
                        <button class="btn btn-danger" onclick="deleteStock('{{ stock_code }}')">删除</button>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>'''
        
        with open(os.path.join(templates_dir, 'stocks.html'), 'w', encoding='utf-8') as f:
            f.write(stocks_html)
        
        # 生成users.html
        users_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>用户管理</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .nav {
            background-color: #333;
            color: white;
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        .nav a {
            color: white;
            text-decoration: none;
            margin: 0 10px;
            padding: 5px 10px;
            border-radius: 3px;
        }
        .nav a:hover {
            background-color: #555;
        }
        .card {
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .btn {
            display: inline-block;
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 5px;
            border: none;
            cursor: pointer;
        }
        .btn:hover {
            background-color: #45a049;
        }
        .btn-danger {
            background-color: #f44336;
        }
        .btn-danger:hover {
            background-color: #da190b;
        }
        .balance {
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>用户管理</h1>
        <div class="nav">
            <a href="/">首页</a>
            <a href="/stocks">股票管理</a>
            <a href="/users">用户管理</a>
        </div>
        
        <div class="card">
            <h2>用户列表</h2>
            <table>
                <tr>
                    <th>用户ID</th>
                    <th>用户名</th>
                    <th>账户余额</th>
                </tr>
                {% for user in users %}
                <tr>
                    <td>{{ user.id }}</td>
                    <td>{{ user.username }}</td>
                    <td class="balance">¥{{ user.balance }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>'''
        
        with open(os.path.join(templates_dir, 'users.html'), 'w', encoding='utf-8') as f:
            f.write(users_html)
        
        # 生成app.py
        app_py = '''from flask import Flask, render_template, request, jsonify
import socket
import json

app = Flask(__name__)

# 连接到后端服务器
def send_request_to_server(request_data):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('localhost', 10024))
        client_socket.send(json.dumps(request_data).encode('utf-8'))
        response = client_socket.recv(1024).decode('utf-8')
        client_socket.close()
        return json.loads(response)
    except Exception as e:
        return {'error': str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stocks')
def stocks():
    response = send_request_to_server({'action': 'get_stocks'})
    stocks = response.get('stocks', {})
    return render_template('stocks.html', stocks=stocks)

@app.route('/add_stock', methods=['POST'])
def add_stock():
    stock_code = request.form['stock_code']
    company_name = request.form['company_name']
    price = float(request.form['price'])
    
    response = send_request_to_server({
        'action': 'add_stock',
        'stock_code': stock_code,
        'company_name': company_name,
        'price': price,
        'admin_password': 'admin123'
    })
    
    return jsonify(response)

@app.route('/delete_stock', methods=['POST'])
def delete_stock():
    stock_code = request.form['stock_code']
    
    response = send_request_to_server({
        'action': 'delete_stock',
        'stock_code': stock_code,
        'admin_password': 'admin123'
    })
    
    return jsonify(response)

@app.route('/users')
def users():
    response = send_request_to_server({
        'action': 'get_users',
        'admin_password': 'admin123'
    })
    users = response.get('users', [])
    return render_template('users.html', users=users)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10027, debug=True)'''
        
        app_py_path = os.path.join('..', 'linux_frontend', 'app.py')
        with open(app_py_path, 'w', encoding='utf-8') as f:
            f.write(app_py)
        
        print("HTML文件和Flask应用已生成")
    
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
        # 注册信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"服务器启动在 {self.host}:{self.port}")
        print("按 Ctrl+C 退出")
        
        # 启动市场模拟线程
        self.market_thread = threading.Thread(target=self.simulate_market)
        self.market_thread.daemon = True
        self.market_thread.start()
        
        try:
            while True:
                client_socket, client_address = self.server_socket.accept()
                print(f"新连接: {client_address}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                client_thread.daemon = True
                client_thread.start()
        except KeyboardInterrupt:
            self.shutdown()
    
    def signal_handler(self, sig, frame):
        print("\n收到退出信号...")
        self.shutdown()
    
    def shutdown(self):
        print("正在保存数据...")
        
        # 保存所有股票数据
        for stock_code in self.stocks:
            stock_info = self.stocks[stock_code]
            conn = sqlite3.connect('stock_trading.db')
            c = conn.cursor()
            c.execute('UPDATE stocks SET price = ?, change = ? WHERE stock_code = ?', 
                     (stock_info['price'], stock_info['change'], stock_code))
            conn.commit()
            conn.close()
        
        print("数据保存完成")
        print("服务器已关闭")
        sys.exit(0)
    
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