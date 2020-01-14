# 放一些常用的工具类
import functools

from flask import session, current_app, g


# 用户是否登陆
def user_login(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id", None)
        # 必须指定，不指定获取不到user
        user = None
        if user_id:
            try:
                from hugely.models import User
                user = User.query.get(user_id)
            except Exception as e:
                current_app.logger.error(e)
        g.user = user
        return f(*args, **kwargs)

    return wrapper
