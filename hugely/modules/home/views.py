from flask import render_template, request, jsonify, current_app
from hugely.models import FeedBack, News, Visitor
from hugely import db
from . import home_blu
from hugely.utils.response_code import RET
import re


@home_blu.route("/")
def home():
    """
    主页
    """
    host = request.headers.get('host')
    terminal = request.headers.get('User-Agent')
    Host = re.match(r'([0-7\.]+):', host).group(1)

    Terminal = re.search(r'\((.+?)\)', terminal).group(1)
    visitor = Visitor()
    visitor.v_ip = Host
    visitor.v_terminal = Terminal

    try:
        db.session.add(visitor)
        db.session.commit()
        return render_template('home/index.html')
    except Exception as e:
        db.session.rollback()
        return render_template('home/index.html')


@home_blu.route("/index")
def index():
    """
    首页
    """
    return render_template('home/index.html')


@home_blu.route("/about")
def about():
    """
    企业介绍
    """
    return render_template('home/about.html')


@home_blu.route("/yuns1")
def yuns1():
    """
    云饰衣
    """
    return render_template('home/yuns1.html')


@home_blu.route("/pgy")
def pgy():
    """
    蒲公英
    """
    return render_template('home/pgy.html')


@home_blu.route("/lbc")
def lbc():
    """
    鲁班尺
    """
    return render_template('home/lbc.html')


@home_blu.route("/meme")
def meme():
    """
    米姆云店
    """
    return render_template('home/meme.html')


@home_blu.route("/sulun")
def sulun():
    """
    苏伦研究院
    """
    return render_template('home/sulun.html')


@home_blu.route("/news")
def news():
    """
    新闻中心:
    数据库查询新闻数据, 分页显示, 每页10条
    """
    page = request.args.get("page", 1)

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    news_list = []
    current_page = 1
    total_page = 1

    try:
        paginate = News.query.filter() \
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
    return render_template('home/news.html', data=context)


@home_blu.route("/contact", methods=["GET", "POST"])
def contact():
    """
    联系我们
    """
    if request.method == "POST":
        name = request.form['name']
        mail = request.form['mail']
        messageForm = request.form['messageForm']

        if not all([name, mail, messageForm]):
            return jsonify(errno=RET.NODATA, errmsg="参数不全")
        mail_re = re.match(r'[a-zA-Z0-9_\.]+@[a-z0-9]+\.[a-z]+', mail)

        if not mail_re:
            return jsonify(errno=RET.NODATA, errmsg="邮箱有误")
        else:
            feedback = FeedBack()
            feedback.fb_user = name
            feedback.fb_email = mail
            feedback.fb_content = messageForm

            try:
                db.session.add(feedback)
                db.session.commit()
                return jsonify(errno=RET.OK)
            except Exception as e:
                db.session.rollback()
                return jsonify(errno=RET.OK)
    else:
        return render_template('home/contact.html')


@home_blu.route("/services")
def services():
    """
    服务
    """
    return render_template('home/services.html')


@home_blu.route("/contact_feedback")
def contact_feedback():
    """
    反馈消息
    """
    return render_template('home/contact_feedback.html')
