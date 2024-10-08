import logging

from flask import Flask, render_template, g
from flask_login import current_user

from celery import Celery, Task

from src.extensions import init_extensions, mongo
from src.utils import ProxyFix
from src import config

from src.blueprints.pages import pages
from src.blueprints.auth.auth import auth

from src.blueprints.admin.admin import admin_bp


def make_celery(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)
            
    celery_app = Celery(
        app.name,
        backend=config.CELERY_RESULT_BACKEND,
        broker=config.CELERY_BROKER_URL
    )
    
    celery_app.Task = FlaskTask
    celery_app.set_default()
    app.extensions['celery'] = celery_app
    
    return celery_app


def create_app():
    app = Flask(__name__)
    app.config['MONGO_URI'] = config.MONGO_URI
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['REMEMBER_COOKIE_DURATION'] = config.REMEMBER_COOKIE_DURATION
    app.config['PERMANENT_SESSION_LIFETIME'] = config.PERMANENT_SESSION_LIFETIME
    
    #next redirects will be stored in session cookies instead of query strings
    app.config['USE_SESSION_FOR_NEXT'] = True
    
    
    app.config['MAIL_SERVER'] = config.MAIL_SERVER
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = config.MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = config.MAIL_PASSWORD
    app.config['MAIL_DEFAULT_SENDER'] = config.MAIL_DEFAULT_SENDER


    
    app.wsgi_app = ProxyFix(app.wsgi_app)

    init_extensions(app)

    # make_celery(app)
    

    app.register_blueprint(pages)
    app.register_blueprint(auth)
    
    app.register_blueprint(admin_bp)

    @app.errorhandler(400)
    def bad_request(e):
        return render_template('pages/400.html')

    @app.errorhandler(401)
    def unauthorized(e):
        return render_template('pages/401.html')


    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('pages/404.html')
    

    @app.after_request
    def set_lang_cookie(response):
        if g.get('set_lang_cookie', False):
            response.set_cookie('lang', g.lang, max_age=60*60*24*365)
            g.set_lang_cookie = False
            
        if g.get('set_user_locale', False):
            mongo.db.users.update_one({'alternative_id': current_user.get_id()}, {'$set': {'preferences.language': g.lang}})
            g.set_user_locale = False
            
        return response

    return app


if __name__ == '__main__':
    app = create_app()
    
    logging.info(f"\n🎉 Starting server on http://{config.HOST}:{config.PORT} 🎉")

    if config.PRODUCTION:
        logging.info("🚨 Running in PRODUCTION mode 🚨")
        
        from waitress import serve
        serve(app, host=config.HOST, port=config.PORT, threads=config.WAITRESS_THREADS)

    else:
        logging.info("🚨 Running in DEVELOPMENT mode 🚨")
        app.run(host=config.HOST, port=config.PORT, debug=True)