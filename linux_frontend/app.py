from flask import Flask, render_template, request, jsonify
import socket
import json

app = Flask(__name__)

# 连接到后端服务器
def send_request_to_server(request_data):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('localhost', 6494))
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
        'price': price
    })
    
    return jsonify(response)

@app.route('/delete_stock', methods=['POST'])
def delete_stock():
    stock_code = request.form['stock_code']
    
    response = send_request_to_server({
        'action': 'delete_stock',
        'stock_code': stock_code
    })
    
    return jsonify(response)

@app.route('/users')
def users():
    response = send_request_to_server({'action': 'get_users'})
    users = response.get('users', [])
    return render_template('users.html', users=users)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)