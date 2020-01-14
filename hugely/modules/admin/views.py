import re
from datetime import datetime, timedelta

from flask import render_template, session, request, url_for, redirect, current_app, g, jsonify
from flask_mail import Message

from hugely import user_login, db, mail
from hugely.models import User, News, FeedBack, Visitor
from hugely.utils.response_code import RET
from . import admin_blu


@admin_blu.before_request
def before_request():
    """
    判断用户是否为管理员:
    如果是管理员, 才能够访问管理员页面, 如果不是管理员, 重定向到首页
    """
    is_admin = session.get("is_admin")
    is_url = request.url.endswith(url_for("admin.login"))
    if not is_admin and not is_url:
        return redirect(url_for("home.index"))


@admin_blu.route("/", methods=["GET", "POST"])
def admin():
    """
    后台登录页
    """
    return redirect(url_for("admin.login"))


@admin_blu.route("/index", methods=["GET", "POST"])
@user_login
def index():
    """
    后台管理首页
    """
    user = g.user
    return render_template("admin/index.html", user=user.to_dict())


@admin_blu.route("/login", methods=["GET", "POST"])
def login():
    """
    管理员登陆页面显示以及登陆:
    get:
    1.如果用户已经登陆，并且为admin用户的话，直接跳转到后台首页
    post:
    1.接收参数用户名和密码
    2.通过用户名找到密码，校验密码是否正确，以及参数的完整性
    3.校验通过后需要保存用户登陆状态
    4.并且跳转到后台首页
    """
    if request.method == "POST":
        data = request.form
        username = data.get("username")
        password = data.get("password")

        if not all([password, username]):
            return render_template("admin/login.html", errmsg="请输入完整信息")

        try:
            user = User.query.filter(User.name == username).first()
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/login.html", errmsg="数据库查询错误")

        if not user:
            return render_template("admin/login.html", errmsg="用户名不存在")

        if not user.check_passowrd(password):
            return render_template("admin/login.html", errmsg="密码错误")

        if not user.is_admin:
            return render_template("admin/login.html", errmsg="权限不够")

        session["user_id"] = user.id
        session["name"] = user.name
        session["is_admin"] = True
        return redirect(url_for("admin.index"))

    user_id = session.get("user_id", None)
    is_admin = session.get("is_admin", False)
    if user_id and is_admin:
        return redirect(url_for("admin.index"))
    else:
        return render_template("admin/login.html")


@admin_blu.route("/logout", methods=["GET", "POST"])
def logout():
    """
    退出登陆
    """
    session.pop("user_id", None)
    session.pop("name", None)
    session.pop("is_admin", None)

    return redirect(url_for("admin.login"))


@admin_blu.route("/visitor_count", methods=["GET", "POST"])
def visitor_count():
    """
    访问量统计:
    1.显示访问总数
    2.访问量月新增人数  （创建时间大于月初）
    3.访问量日新增人数  （创建时间大于当天开始）
    4.访问活跃数。
    """
    total_count = 0
    month_count = 0
    # create_time 是datetime.datetime(2018, 7, 24, 20, 54, 41, 668462) 可以进行比较
    # 1.先找出当月的第一天"2018-07-01"
    # 2.获取当前年份和月份

    # 访问量总数
    try:
        total_count = Visitor.query.count()
    except Exception as e:
        current_app.logger.error(e)

    now = datetime.now()
    month_begin_date_str = "%d-%02d-01" % (now.year, now.month)
    # 转化为datetime.datetime类型
    month_begin_date = datetime.strptime(month_begin_date_str, "%Y-%m-%d")
    try:
        month_count = Visitor.query.filter(Visitor.create_time > month_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)

    day_count = 0
    day_begin_date_str = "%d-%02d-%02d" % (now.year, now.month, now.day)
    # 转化为datetime.datetime类型
    day_begin_date = datetime.strptime(day_begin_date_str, "%Y-%m-%d")
    try:
        day_count = Visitor.query.filter(Visitor.create_time > day_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)
    # 拆线图数据

    active_time = []
    active_count = []

    for i in range(0, 31):
        # 取到某一天的0点0分
        begin_date = day_begin_date - timedelta(days=i)
        # 取到下一天的0点0分
        end_date = day_begin_date - timedelta(days=(i - 1))
        count = Visitor.query.filter(Visitor.update_time >= begin_date,
                                     Visitor.update_time < end_date).count()
        active_count.append(count)
        active_time.append(begin_date.strftime('%Y-%m-%d'))

    # 反转，让最近的一天显示在最后
    active_time.reverse()
    active_count.reverse()

    data = {
        "total_count": total_count,
        "day_count": day_count,
        "month_count": month_count,
        "active_time": active_time,
        "active_count": active_count
    }
    return render_template("admin/visitor_count.html", data=data)


@admin_blu.route("/news_release", methods=["GET", "POST"])
@user_login
def news_release():
    """
    新闻发布:
    从表单中获取新闻数据, 存储到数据库
    """
    if request.method == "POST":

        data = request.form
        title = data.get("title")
        link = data.get("link")
        digest = data.get("digest")

        if not all([title, link, digest]):
            return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

        # 正则匹配链接网址
        if not re.match(
                r"(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*,]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)|([a-zA-Z]+.\w+\.+[a-zA-Z0-9\/_]+)",
                link):
            return jsonify(errno=RET.PARAMERR, errmsg="网址有误")

        # 初始化新闻模型，并设置相关数据
        news = News()
        news.title = title
        news.link = link
        news.digest = digest
        news.user_id = g.user.id

        # 保存到数据库
        try:
            db.session.add(news)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            db.session.rollback()
            return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
        # 返回结果
        return jsonify(errno=RET.OK, errmsg="发布成功！")
    else:
        return render_template("admin/news_release.html")


@admin_blu.route("/news_review", methods=["GET", "POST"])
def news_review():
    """
    新闻审核:
    数据库查询新闻数据, 分页显示, 每页10条
    """
    # 获取查询字符串参数
    page = request.args.get("page", 1)
    keywords = request.args.get("keywords", "")

    # 分页显示新闻列表数据
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    news_list = []
    current_page = 1
    total_page = 1

    filters = []
    if keywords:
        filters.append(News.title.contains(keywords))

    try:
        paginate = News.query.filter(*filters) \
            .order_by(News.create_time.desc()) \
            .paginate(page, 10, False)

        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_dict())

    context = {"total_page": total_page,
               "current_page": current_page,
               "news_list": news_dict_list
               }
    return render_template('admin/news_review.html', data=context)


@admin_blu.route('/news_edit', methods=["GET", "POST"])
@user_login
def news_edit():
    """
    新闻编辑:
    1.根据news_id, 数据库查询新闻数据,
    2.修改新闻数据, 保存到数据库
    """
    if request.method == "GET":
        news_id = request.args.get("news_id")
        if not news_id:
            return render_template('admin/news_review.html', data={"errmsg": "未查询到此新闻"})
        # 通过id查询新闻
        news = None
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)

        if not news:
            return render_template('admin/news_review.html', data={"errmsg": "未查询到新闻数据"})
        data = {"news": news.to_dict()}
        return render_template('admin/news_edit.html', data=data)

    data = request.form
    news_id = data.get("news_id")
    title = data.get("title")
    link = data.get("link")
    digest = data.get("digest")

    # 判断数据是否有值
    if not all([news_id, title, link, digest]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")

    # 设置相关数据
    news.id = news_id
    news.title = title
    news.link = link
    news.digest = digest
    news.user_id = g.user.id

    # 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    return jsonify(errno=RET.OK, errmsg="编辑成功!")


@admin_blu.route("/news_delete", methods=["GET", "POST"])
def news_delete():
    """
    新闻删除:
    1.根据news_id, 数据库查询新闻数据, 表单显示;
    2.根据news_id, 从数据库删除新闻数据
    """
    # 获取查询字符串参数
    if request.method == "GET":
        news_id = request.args.get("news_id")
        if not news_id:
            return render_template('admin/news_review.html', data={"errmsg": "未查询到此新闻"})
        # 通过id查询新闻
        news = None
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)

        if not news:
            return render_template('admin/news_review.html', data={"errmsg": "未查询到新闻数据"})
        data = {"news": news.to_dict()}
        return render_template('admin/news_delete.html', data=data)

    data = request.form
    news_id = data.get("news_id")

    # 判断数据是否有值
    if not news_id:
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")

    try:
        db.session.delete(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="删除数据失败")
    return jsonify(errno=RET.OK, errmsg="删除成功!")


@admin_blu.route("/feedback_review", methods=["GET", "POST"])
def feedback_review():
    """
    反馈审核
    """
    page = request.args.get("page", 1)
    keywords = request.args.get("keywords", "")

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    feedback_list = []
    current_page = 1
    total_page = 1

    filters = []
    if keywords:
        filters.append(FeedBack.fb_content.contains(keywords))

    try:
        paginate = FeedBack.query.filter(*filters) \
            .order_by(FeedBack.create_time.desc()) \
            .paginate(page, 10, False)

        feedback_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    feedback_dict_list = []
    for feedback in feedback_list:
        feedback_dict_list.append(feedback.to_dict())

    context = {"total_page": total_page,
               "current_page": current_page,
               "feedback_list": feedback_dict_list
               }
    return render_template("admin/feedback_review.html", data=context)


@admin_blu.route("/feedback_reply", methods=["GET", "POST"])
def feedback_reply():
    """
    反馈回复
    """
    if request.method == "GET":
        feedback_id = request.args.get("feedback_id")
        page = request.args.get("page")

        if feedback_id:
            feedback = None
            try:
                feedback = FeedBack.query.get(feedback_id)
            except Exception as e:
                current_app.logger.error(e)
            data = {"feedback": feedback.to_dict(), "page": page}
            return render_template('admin/feedback_reply.html', data=data)
        else:
            id = int(request.args.get('fb_id'))
            page = request.args.get('page')
            email = request.args.get('fb_email')
            title = request.args.get('title')
            content = request.args.get('content')

            if not all([title, content]):
                return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

            msg = Message('{}'.format(title), sender='1019178132@qq.com', recipients=['{}'.format(email)])
            msg.body = content
            with current_app.app_context():
                mail.send(msg)
                FeedBack.query.filter_by(id=id).update({"fb_whether_reply": "是"})
                db.session.commit()
                return redirect('admin/feedback_review?page=' + page)


@admin_blu.route("/feedback_delete", methods=["GET", "POST"])
def feedback_delete():
    """
    反馈删除:
    1.根据id, 数据库查询反馈数据, 表单显示;
    2.根据id, 从数据库删除反馈数据
    """
    # 获取查询字符串参数
    if request.method == "GET":
        feedback_id = request.args.get("feedback_id")
        if not feedback_id:
            return render_template('admin/news_review.html', data={"errmsg": "未查询到此反馈"})
        # 通过id查询反馈内容
        feedback = None
        try:
            feedback = FeedBack.query.get(feedback_id)
        except Exception as e:
            current_app.logger.error(e)

        if not feedback:
            return render_template('admin/news_review.html', data={"errmsg": "未查询到反馈数据"})
        data = {"feedback": feedback.to_dict()}
        return render_template('admin/feedback_delete.html', data=data)

    data = request.form
    feedback_id = data.get("feedback_id")

    # 判断数据是否有值
    if not feedback_id:
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    feedback = None
    try:
        feedback = FeedBack.query.get(feedback_id)
    except Exception as e:
        current_app.logger.error(e)
    if not feedback:
        return jsonify(errno=RET.NODATA, errmsg="未查询到反馈数据")

    try:
        db.session.delete(feedback)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="删除数据失败")
    return jsonify(errno=RET.OK, errmsg="删除成功!")
