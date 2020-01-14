# 数据库模型类

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from . import db


class BaseModel(object):
    """模型基类，为每个模型补充创建时间与更新时间"""
    create_time = db.Column(db.DateTime, default=datetime.now)  # 记录的创建时间
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)  # 记录的更新时间


class User(BaseModel, db.Model):
    """用户"""
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)  # 用户编号
    name = db.Column(db.String(32), unique=True, nullable=False)  # 用户名称
    password_hash = db.Column(db.String(128), nullable=False)  # 加密的密码
    is_admin = db.Column(db.Boolean, default=False)  # 是否管理员
    last_login = db.Column(db.DateTime, default=datetime.now)  # 最后一次登录时间

    @property
    def password(self):
        raise AttributeError("当前属性不可读")

    @password.setter
    def password(self, value):
        self.password_hash = generate_password_hash(value)

    def check_passowrd(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        resp_dict = {
            "id": self.id,
            "name": self.name,
            "last_login": self.last_login.strftime("%Y-%m-%d %H:%M:%S"),
        }
        return resp_dict


class News(BaseModel, db.Model):
    """新闻"""
    __tablename__ = "news"

    id = db.Column(db.Integer, primary_key=True)  # 新闻编号
    title = db.Column(db.String(256), nullable=False)  # 新闻标题
    link = db.Column(db.String(256), nullable=False)  # 链接网址
    digest = db.Column(db.String(512), nullable=False)  # 新闻摘要
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # 新闻的发布者ID
    user = db.relationship('User', backref='news')  # 关联数据库表 user

    def to_dict(self):
        resp_dict = {
            "id": self.id,
            "title": self.title,
            "link": self.link,
            'digest': self.digest,
            "user_name": self.user.name,
            "create_time": self.create_time.strftime("%Y-%m-%d"),
        }
        return resp_dict


class FeedBack(BaseModel, db.Model):
    """反馈"""
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)  # 反馈编号
    fb_user = db.Column(db.String(20), nullable=False)  # 反馈名称
    fb_email = db.Column(db.String(30), nullable=False)  # 反馈邮箱
    fb_content = db.Column(db.Text, nullable=False)  # 反馈内容
    fb_whether_reply = db.Column(db.Text(20), nullable=False, default='否')  # 反馈是否回复

    def to_dict(self):
        resp_dict = {
            "id": self.id,
            "fb_user": self.fb_user,
            "fb_email": self.fb_email,
            "fb_content": self.fb_content,
            "fb_whether_reply": self.fb_whether_reply,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        return resp_dict


class Visitor(BaseModel, db.Model):
    """访问量"""
    __tablename__ = "visitor"

    id = db.Column(db.Integer, primary_key=True)  # 访问编号
    v_ip = db.Column(db.String(30), nullable=False)  # 访问ip
    v_terminal = db.Column(db.String(256), nullable=False)  # 访问终端

    def to_dict(self):
        resp_dict = {
            "id": self.id,
            "v_ip": self.v_ip,
            "v_terminal": self.v_terminal,
            "create_time": self.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        return resp_dict
