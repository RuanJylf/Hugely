from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from hugely import create_app, db
from hugely.models import User

# 设置运行环境
app = create_app("development")
manager = Manager(app)

# 数据库迁移
Migrate(app, db)
manager.add_command("db", MigrateCommand)


# 创建管理员账户
@manager.option("-u", "--username", dest='username')
@manager.option("-p", "--password", dest='password')
def create_admin(username, password):
    if not all([username, password]):
        print("参数不全")

    user = User()
    user.name = username
    user.password = password
    user.is_admin = True

    try:
        db.session.add(user)
        db.session.commit()
        print("创建成功")
    except Exception as e:
        db.session.rollback()
        print("创建失败")
        print(e)


if __name__ == "__main__":
    manager.run()
