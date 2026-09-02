from datetime import timedelta
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager 

# Core and Operation Blueprints
from routes.category_routes import category_bp
from routes.product_routes import product_bp
from routes.supplier_routes import supplier_bp
from routes.stock_in_routes import stock_in_bp
from routes.stock_out_routes import stock_out_bp
from routes.sales_routes import sales_bp
from routes.report_routes import report_bp
from routes.forcast_routes import forecast_bp
from routes.reorder_routes import reorder_bp
from routes.alert_routes import alert_bp
from routes.analytics_routes import analytics_bp
from routes.auth_routes import auth_bp
from routes.backup_routes import backup_bp
from routes.inventory_routes import inventory_bp
from routes.stock_movement_routes import stock_movement_bp

app = Flask(__name__)

CORS(app)

app.config["JWT_SECRET_KEY"] = "super-secret-store-key-12345" 
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=30)
jwt = JWTManager(app)

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(inventory_bp, url_prefix="/inventory") 
app.register_blueprint(backup_bp, url_prefix="/backup")

# Standard Route Mappings
app.register_blueprint(category_bp)
app.register_blueprint(product_bp)
app.register_blueprint(supplier_bp)
app.register_blueprint(stock_in_bp)
app.register_blueprint(stock_out_bp)
app.register_blueprint(sales_bp)
app.register_blueprint(report_bp)
app.register_blueprint(forecast_bp)
app.register_blueprint(reorder_bp)
app.register_blueprint(alert_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(stock_movement_bp)

# Duplicate registration lines for backup_bp and inventory_bp have been completely removed

@app.route("/")
def home():
    """
    Root status check endpoint to confirm the server instance is online and accepting connections.
    """
    return jsonify({
        "message": "Smart Inventory API is running!"
    })

if __name__ == "__main__":
    app.run(debug=True)
