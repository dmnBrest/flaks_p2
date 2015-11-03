# -*- coding: utf-8 -*-

from flask import Flask, request_started, session, request
from flask_debugtoolbar import DebugToolbarExtension
from flask_redis import Redis
from flask.ext.sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask.ext.security import Security, SQLAlchemyUserDatastore
from flask_security.forms import ConfirmRegisterForm
from wtforms import StringField, validators
from flask_wtf import RecaptchaField
from flask_wtf.csrf import CsrfProtect
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from jinja2 import evalcontextfilter, Markup, escape
import bbcode, re

app = Flask(__name__)
app.config.from_object('config')

redis_store = Redis(app)

app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')

@app.template_filter()
@evalcontextfilter
def nl2br(eval_ctx, value):
	result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br>\n') \
		for p in _paragraph_re.split(escape(value)))
	if eval_ctx.autoescape:
		result = Markup(result)
	return result


db = SQLAlchemy(app)
mail = Mail(app)

CsrfProtect(app)

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)


# ----------- LOGGER ----------------------
if not app.debug:
	import logging
	from logging.handlers import SMTPHandler
	mail_handler = SMTPHandler(mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
								fromaddr='server-error@salesforce-developer.net',
								toaddrs=app.config['ADMINS_MAILS'],
								subject='Salesforce-Developer.NET Failed',
								credentials=(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD']),
								secure=()
	)
	mail_handler.setLevel(logging.ERROR)
	app.logger.addHandler(mail_handler)
	file_handler = logging.FileHandler(filename=app.config['LOG_FILE'])
	file_handler.setLevel(logging.WARNING)
	app.logger.addHandler(file_handler)


# ------------ BBCODE PARSER CUSTOM TAGS -----------
bbcode_parser = bbcode.Parser(replace_links=False)
bbcode_parser.add_simple_formatter('h2', '<h2>%(value)s</h2>', swallow_trailing_newline=True)
bbcode_parser.add_simple_formatter('h3', '<h3>%(value)s</h3>', swallow_trailing_newline=True)
bbcode_parser.add_simple_formatter('h4', '<h4>%(value)s</h4>', swallow_trailing_newline=True)
bbcode_parser.add_simple_formatter('p', '<p>%(value)s</p>', swallow_trailing_newline=True)
bbcode_parser.add_simple_formatter('br', '<br />', standalone=True)
bbcode_parser.add_simple_formatter('img', '<span class="article-img"><img src="%(value)s"></span>', replace_links=False, swallow_trailing_newline=True)
bbcode_parser.add_simple_formatter('code', '<pre class="prettyprint linenums"><code>%(value)s</code></pre>', render_embedded=False, transform_newlines=False, swallow_trailing_newline=True)

def render_quote(tag_name, value, options, parent, context):
	author = u''
	# [quote author=Somebody]
	if 'author' in options:
		author = options['author']
	# [quote=Somebody]
	elif 'quote' in options:
		author = options['quote']
	# [quote Somebody]
	elif len(options) == 1:
		key, val = options.items()[0]
		if val:
			author = val
		elif key:
			author = key
	# [quote Firstname Lastname]
	elif options:
		author = ' '.join([k for k in options.keys()])
	extra = '<div class="quote_author"><u>%s</u>:</div>' % author if author else ''
	return '<blockquote>%s<p>%s</p></blockquote>' % (extra, value)

# Now register our new quote tag, telling it to strip off whitespace, and the newline after the [/quote].
bbcode_parser.add_formatter('quote', render_quote, strip=True, swallow_trailing_newline=True)

domain_re = re.compile(r'(?im)(?:www\d{0,3}[.]|[a-z0-9.\-]+[.](?:com|net|org|edu|biz|gov|mil|info|io|name|me|tv|us|uk|mobi))')

def render_url(name, value, options, parent, context):
	if options and 'url' in options:
		# Option values are not escaped for HTML output.
		# href = self._replace(options['url'], self.REPLACE_ESCAPE)
		for find, repl in bbcode_parser.REPLACE_ESCAPE:
			options['url'] = options['url'].replace(find, repl)
		href = options['url']
	else:
		href = value
	# Completely ignore javascript: and data: "links".
	if re.sub(r'[^a-z0-9+]', '', href.lower().split(':', 1)[0]) in ('javascript', 'data', 'vbscript'):
		return ''
	# Only add the missing http:// if it looks like it starts with a domain name.
	if '://' not in href and domain_re.match(href):
		href = 'http://' + href
	return '<a href="%s" rel="nofollow">%s</a>' % (href.replace('"', '%22'), value)
bbcode_parser.add_formatter('url', render_url, replace_links=False, replace_cosmetic=False)

# administrator list
ADMINS = ['admin@p2.dev']

from app import views, models

class ExtendedRegisterForm(ConfirmRegisterForm):
	username = StringField('Username',
						   [validators.DataRequired(message='Username not provided'),
							validators.Length(min=4, max=25),
							validators.Regexp('^[a-zA-Z0-9_-]+$',  message='Wrong Username format. "a-z", "A-Z", "0-9", "_" and "-" characters are allowed. Min 4 character')])
	recaptcha = RecaptchaField('Captcha')

	def validate(self):
		#check for username
		success = True
		if not super(ExtendedRegisterForm, self).validate():
			success = False
		if models.User.query.filter_by(username = self.username.data.strip()).first():
			self.username.errors.append("Username already taken")
			success = False
		return success

user_datastore = SQLAlchemyUserDatastore(db, models.User, models.Role)
security = Security(app, user_datastore, confirm_register_form=ExtendedRegisterForm)

# TOOLBAR
toolbar = DebugToolbarExtension(app)

from seed import seed_db
@manager.command
def seed():
	seed_db()
	print('Seed FINISHED successfully.')

@manager.shell
def make_shell_context():
	return dict(app=app, db=db, models=models)


@request_started.connect_via(app)
def before_request_started(app, **extra):
	if not request.path.startswith('/static') and \
			not request.path.startswith('/_') and \
			not request.path.startswith('/pictures') and \
			not request.path.startswith('/favicon.ico') and \
			not request.path.startswith('/auth'):
		r = request.path
		session['prev_url'] = request.path
