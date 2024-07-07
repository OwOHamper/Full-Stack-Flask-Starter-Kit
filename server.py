from flask import Flask, render_template, send_from_directory, request, g
import logging

from werkzeug.middleware.proxy_fix import ProxyFix
from flask_compress import Compress
from flask_minify import Minify
from flask_talisman import Talisman

from flask_babel import Babel

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src import config
from src.localization import get_locale

from src.blueprints.pages import pages
from src.blueprints.auth import auth, login_manager

from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_seasurf import SeaSurf

app = Flask(__name__)
app.config['MONGO_URI'] = config.MONGO_URI
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['REMEMBER_COOKIE_DURATION'] = config.REMEMBER_COOKIE_DURATION
app.config['PERMANENT_SESSION_LIFETIME'] = config.PERMANENT_SESSION_LIFETIME


#You can enable force_https if you have a SSL certificate and everything set up
#Also depends on your proxy setup
Talisman(app, force_https=False, content_security_policy=config.CSP)
app.wsgi_app = ProxyFix(app.wsgi_app)

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=app.config['MONGO_URI'],
    strategy='fixed-window', # 'moving-window' when you want to prevent burst attacks
)

mongo = PyMongo(app)
bcrypt = Bcrypt(app)


babel = Babel(app, locale_selector=get_locale)
csrf = SeaSurf(app)


if config.PRODUCTION:
    Compress(app)
    Minify(app=app, html=True, js=True, cssless=True, go=False)


login_manager.init_app(app)

app.register_blueprint(pages)
app.register_blueprint(auth, mongo=mongo, bcrypt=bcrypt)



@app.errorhandler(404)
def page_not_found(e):
    return render_template('pages/404.html')

@app.after_request
def set_lang_cookie(response):
    if g.get('set_cookie', False):
        response.set_cookie('lang', g.lang, max_age=60*60*24*365)
    return response

if __name__ == '__main__':
    logging.info(f"\n🎉 Starting server on http://{config.HOST}:{config.PORT} 🎉")
    
    if config.PRODUCTION:
        logging.info("🚨 Running in PRODUCTION mode 🚨")
        
        from waitress import serve
        serve(app, host=config.HOST, port=config.PORT)
    
    else:
        logging.info("🚨 Running in DEVELOPMENT mode 🚨")
        app.run(host=config.HOST, port=config.PORT, debug=True)