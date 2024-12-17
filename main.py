from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from dotenv import load_dotenv
from flasgger import Swagger
import datetime
import os

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///bonus_program.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'default_jwt_secret_key')

db = SQLAlchemy(app)
jwt = JWTManager(app)

swagger = Swagger(app)  # Инициализируем Swagger

# Модель данных class User
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    spending = db.Column(db.Float, default=0.0)
    level = db.Column(db.String(20), default="Bronze")

class BonusLevels(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    level_name = db.Column(db.String(20), unique=True, nullable=False)
    min_spending = db.Column(db.Float, nullable=False)

# Инициализация базы данных
@app.before_request
def init():
    with app.app_context():
        db.create_all()
        if not BonusLevels.query.first():
            levels = [
                BonusLevels(level_name="Silver", min_spending=1000),
                BonusLevels(level_name="Gold", min_spending=5000),
                BonusLevels(level_name="Platinum", min_spending=10000),
            ]
            db.session.bulk_save_objects(levels)
            db.session.commit()

# Эндпоинт для регистрации пользователя
@app.route('/auth/register', methods=['POST'])
def register():
    """
    User registration
    ---
    parameters:
      - name: credentials
        in: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
              example: "john_doe"
            password:
              type: string
              example: "password123"
    responses:
      201:
        description: User registered successfully
      400:
        description: User already exists
    """
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "User already exists"}), 400

    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "User registered successfully"}), 201

# Эндпоинт для получения токена
# я получаю id юзера через токен 
@app.route('/auth/login', methods=['POST'])
def login():
    """
    User login and token generation
    ---
    parameters:
      - name: credentials
        in: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
              example: "john_doe"
            password:
              type: string
              example: "password123"
    responses:
      200:
        description: User successfully logined
        schema:
          id: token_response
          properties:
            msg:
              type: string
              example: "User successfully logined"
            token:
              type: string
              example: "JWT_TOKEN_HERE"
      401:
        description: Invalid credentials
    """
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return jsonify({"msg": "Invalid credentials"}), 401

    token = create_access_token(identity=str(user.id), expires_delta=datetime.timedelta(hours=1))
    return jsonify({"msg": "User successfully logined", "token": token})

# Эндпоинт для получения данных о бонусной программе
# я получаю id юзера через токен 
@app.route('/bonus', methods=['GET'])
@jwt_required()
def bonus():
    """
    Get user bonus program information
    ---
    parameters:
      - name: Authorization
        in: header
        required: true
        type: string
        description: "JWT token"
    responses:
      200:
        description: Current bonus level and next level info
        schema:
          id: bonus_response
          properties:
            current_level:
              type: string
              example: "Silver"
            spending:
              type: float
              example: 1200.0
            next_level:
              type: object
              properties:
                level_name:
                  type: string
                  example: "Gold"
                min_spending:
                  type: float
                  example: 3800.0
      404:
        description: User not found
    """
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user:
        return jsonify({"msg": "User not found"}), 404

    current_level = user.level
    spending = user.spending

    next_level = BonusLevels.query.filter(BonusLevels.min_spending > spending).order_by(BonusLevels.min_spending).first()
    next_level_data = {
        "level_name": next_level.level_name,
        "min_spending": next_level.min_spending - spending
    } if next_level else None

    return jsonify({
        "current_level": current_level,
        "spending": spending,
        "next_level": next_level_data
    })

# я получаю id юзера через токен 
@app.route('/transactions', mettransactionshods=['POST'])
@jwt_required()
def add_spending():
    """
    Add spending to user's account and update their bonus level
    ---
    parameters:
      - name: Authorization
        in: header
        required: true
        type: string
        description: "JWT token"

      - name: spending_amount
        in: body
        required: true
        type: object
        description: "Amount of spending to be added. Must be a positive number."
        example: 
          {
            "spending_amount": 100.0
          }
        properties:
          spending_amount:
            type: number
            format: float
            description: "Amount of spending"
            example: 100.0
            minValue: 0.01

    responses:
      200:
        description: Spending added successfully, and user level updated.
        schema:
          id: spending_response
          properties:
            msg:
              type: string
              example: "Spending added successfully"
            new_spending:
              type: float
              example: 1500.0
            new_level:
              type: string
              example: "Gold"
      400:
        description: Invalid spending amount. The amount must be a positive number.
      404:
        description: User not found. The user associated with the token does not exist.
    """
    
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user:
        return jsonify({"msg": "User not found"}), 404

    data = request.json
    spending_amount = data.get('spending_amount', 0)

    if not isinstance(spending_amount, (int, float)) or spending_amount <= 0:
        return jsonify({"msg": "Invalid spending amount"}), 400

    # Обновляем траты пользователя
    user.spending += spending_amount

    # Проверяем новый уровень пользователя
    new_level = BonusLevels.query.filter(BonusLevels.min_spending <= user.spending).order_by(BonusLevels.min_spending.desc()).first()
    if new_level:
        user.level = new_level.level_name

    db.session.commit()

    return jsonify({
        "msg": "Spending added successfully",
        "new_spending": user.spending,
        "new_level": user.level
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5001)))