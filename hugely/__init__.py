import logging
from logging.handlers import RotatingFileHandler
import redis
from flask import Flask, g, render_template
from flask_mail import Mail
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from config import config

from hugely.utils.common import user_login

db = SQLAlchemy()

mail = Mail()
redis_store = None


def set_log(config_name):
    # 设置日志的记录等级
    logging.basicConfig(level=config[config_name].LOG_DEVEL)  # 调试debug级
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10, encoding="utf-8")
    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)


def create_app(config_name):
    """创建应用"""

    set_log(config_name)
    app = Flask(__name__)

    # 从对象中加载配置
    app.config.from_object(config[config_name])

    # 在初始化app的时候传入app
    db.init_app(app)

    # 在初始化时传入mail
    mail.init_app(app)

    # 配置redis数据库
    global redis_store
    redis_store = redis.StrictRedis(host=config[config_name].REDIS_HOST, port=config[config_name].REDIS_PORT,
                                    decode_responses=True)

    # 开启csrf保护, 做保护和验证工作。具体返回到表单中和cookie需要我们自己设定。
    CSRFProtect(app)

    # 指定session的储存方式
    Session(app)

    # 全局处理404页面
    @app.errorhandler(404)
    @user_login
    def error_handler(_):
        data = {
            "user": g.user.to_dict() if g.user else None
        }
        return render_template("home/404.html", data=data)

    @app.after_request
    def after_request(response):
        """在响应最后设置csrf_token到cookie中"""
        csrf_token = generate_csrf()
        response.set_cookie("csrf_token", csrf_token)
        return response

    # 注册蓝图
    from hugely.modules.home import home_blu
    app.register_blueprint(home_blu)

    from hugely.modules.admin import admin_blu
    app.register_blueprint(admin_blu)

    return app
