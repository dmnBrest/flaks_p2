# -*- coding: utf-8 -*-

from app import app, db, bbcode_parser, redis_store
from flask import request, render_template, redirect, url_for, send_from_directory, abort, flash, g, jsonify
import datetime
import os
from PIL import Image
import simplejson
import traceback
from werkzeug.utils import secure_filename
import imghdr
from models import User, Picture, Post, Meta, Forum, ForumTopic, ForumPost, Breadcrumb
from services import ForumPostService, ForumTopicService
from forms import BlogPostForm, UserForm, SettingsForm, ForumTopicForm, ForumPostForm
from flask.ext.security import login_required, roles_required, current_user
from flask.ext.security.utils import verify_password, encrypt_password
from unidecode import unidecode
from sqlalchemy.orm import joinedload, load_only, undefer_group
import random


@app.route('/')
#@login_required
def home():
	#request.form['username']
	#flash('DOOM FLASH!!!!', 'info')
	#flash('DOOM FLASH!!!!', 'error')
	#flash('DOOM FLASH!!!!', 'success')

	# msg = Message("Hello", sender="from@example.com", recipients=["to@example.com"])
	# msg.body = "testing"
	# msg.html = "<b>testing</b>"
	# mail.send(msg)



	# u1 = User.query.first()
	# u1.first_name = 'f1'
	# u1.last_name = 'l1'
	# u1.current_login_ip = '37.212.40.101'
	# u1.slug = None
	# db.session.commit()

	# p = redis_store.get('potato')
	# if p is None:
	# 	redis_store.set('potato', 'XXXXX')
	# app.logger.debug(p)

	# p1 = None
	# if current_user.is_authenticated():
	# 	t1 = ForumTopic.query.first()
	# 	p1 = ForumPost(title='p XX 1', body='Lorem ipsum dolor sit amet, consectetur adipisicing elit. ', forum_id=t1.forum.id, topic_id=t1.id, user_id=current_user.id)
	# 	p1 = ForumPostService.CreateNewForumPost(p1)
	#
	# print(p1.topic.title)
	# print(current_user.fullname())

	return render_template('home.html')



# ------------- PICTURES ------------------
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
IGNORED_FILES = set(['.gitignore'])

@app.route('/pictures', methods=['GET', 'POST'])
@roles_required('editor')
def pictures():
	if request.method == 'POST':
		file = request.files['file']

		if file:
			filename = secure_filename(unidecode(file.filename))
			filename = str(current_user.id+1024)+'_'+filename
			filename = gen_file_name(filename)
			mimetype = file.content_type

			file_ext = imghdr.what(file)

			app.logger.debug(file_ext)

			if not file_ext in ALLOWED_EXTENSIONS:
				result = {"error": "Filetype not allowed",
						  "name": filename,
						  "type": mimetype,
						  "size": 0,}

			else:
				# save file to disk
				uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
				file.save(uploaded_file_path)

				p = Picture(filename=filename, user=current_user)
				db.session.add(p)

				# create thumbnail after saving
				if mimetype.startswith('image'):
					create_thumbnail(filename, 256)

				# get file size after saving
				size = os.path.getsize(uploaded_file_path)

				# return json for js call back
				result = {"name": p.filename,
						 "url": p.picture_path(),
						 "thumbnailUrl": p.thumb_path(256),
						 }

				db.session.commit()

			return simplejson.dumps({"files": [result]})

	if request.method == 'GET':
		pics = Picture.query.filter_by(user_id=current_user.id).all()
		inline = request.args.get('inline', 'false')
		type = request.args.get('type', '')
		if inline == 'true':
			pic_layout='layout_empty.html'
		else:
			pic_layout='layout.html'
		return render_template('pictures.html', pics=pics, pic_layout=pic_layout, type=type)

	return redirect(url_for('home'))

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def gen_file_name(filename):
	i = 1
	while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
		name, extension = os.path.splitext(filename)
		filename = '%s_%s%s' % (name, str(i), extension)
		i = i + 1
	return filename

def create_thumbnail(image, basewidth):
	try:
		size = (basewidth, basewidth)
		img = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], image))
		# wpercent = (basewidth/float(img.size[0]))
		# hsize = int((float(img.size[1])*float(wpercent)))
		# img = img.resize((basewidth,hsize), PIL.Image.ANTIALIAS)

		width, height = img.size
		if width > height:
			delta = width - height
			left = int(delta/2)
			upper = 0
			right = height + left
			lower = height
		else:
			delta = height - width
			left = 0
			upper = int(delta/2)
			right = width
			lower = width + upper

		img = img.crop((left, upper, right, lower))

		img.thumbnail(size, Image.ANTIALIAS)
		img.save(os.path.join(app.config['THUMBNAIL_FOLDER'], 'thumb'+str(basewidth)+'_'+image), quality=90, dpi=(72,72))

		return True

	except:
		print traceback.format_exc()
		return False

# -------------- GET PICTURE for DEV SERVER ----------
@app.route("/pictures/<string:filename>", methods=['GET'])
def get_picture(filename):
	return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER']), filename=secure_filename(filename))

@app.route("/pictures/thumbs/<string:filename>", methods=['GET'])
def get_thumbnail(filename):
	return send_from_directory(os.path.join(app.config['THUMBNAIL_FOLDER']), filename=secure_filename(filename))

@app.route("/pictures/avatars/<string:filename>", methods=['GET'])
def get_avatars(filename):
	return send_from_directory(os.path.join(app.config['AVATAR_FOLDER']), filename=secure_filename(filename))

# ------------- EDITOR -------------------------------
@app.route("/blog")
@app.route("/blog/page/<int:page>")
def blog_list(page=1):
	g.breadcrumbs = []
	g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
	g.breadcrumbs.append(Breadcrumb('/blog', 'Blog'))
	posts = Post.query.options(joinedload('user')).\
			filter(Post.published_at != None).\
			order_by(Post.published_at.desc()).\
			paginate(page, 10, True)
	total_drafts = None
	if current_user.has_role('editor'):
		total_drafts = Post.query.options(load_only('id')).filter(Post.user_id == current_user.id, Post.published_at == None).count()
	meta = Meta(title='Blog | Salesforce-Developer.NET',
				description='Blog for Salesforce Developers with main technical information and examples of apex code.',
				keywords='salesforce blog, apex blog, visualforce blog'
				)

	return render_template('blog_list.html', posts=posts, meta=meta, total_drafts=total_drafts)

@app.route("/blog/author/<string:user_slug>")
@app.route("/blog/author/<string:user_slug>/page/<int:page>")
def blog_by_author(user_slug, page=1):
	user = User.query.filter_by(slug=user_slug).first_or_404()
	g.breadcrumbs = []
	g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
	g.breadcrumbs.append(Breadcrumb('/blog', 'Blog'))
	g.breadcrumbs.append(Breadcrumb('', user.fullname()))
	posts = Post.query.options(joinedload('user')).\
			filter(Post.user_id == user.id, Post.published_at != None).\
			order_by(Post.published_at.desc()).\
			paginate(page, 10, True)
	total_drafts = None
	if current_user.has_role('editor'):
		total_drafts = Post.query.options(load_only('id')).filter(Post.user_id == current_user.id, Post.published_at == None).count()
	meta = Meta(title='Articles by '+user.fullname()+' | Salesforce-Developer.NET',
				description='All articler by '+user.fullname()+' published on Salesforce-Developer.net',
				keywords='salesforce articles, '+user.fullname()
				)

	return render_template('blog_list.html', posts=posts, meta=meta, author=user, total_drafts=total_drafts)

@app.route("/blog/drafts/")
@app.route("/blog/drafts/page/<int:page>")
@roles_required('editor')
def blog_my_drafts(page=1):
	g.breadcrumbs = []
	g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
	g.breadcrumbs.append(Breadcrumb('/blog', 'Blog'))
	g.breadcrumbs.append(Breadcrumb('', 'My Drafts'))
	posts = Post.query.options(joinedload('user')).\
			filter(Post.user_id == current_user.id, Post.published_at == None).\
			order_by(Post.created_at.desc()).\
			paginate(page, 10, True)
	total_drafts = None
	if current_user.has_role('editor'):
		total_drafts = Post.query.options(load_only('id')).filter(Post.user_id == current_user.id, Post.published_at == None).count()
	meta = Meta(title='My Drafts | Salesforce-Developer.NET',
				description='My drafts on Salesforce-Developer.net',
				keywords='my drafts'
				)

	return render_template('blog_list.html', posts=posts, meta=meta, my_drafts=True, total_drafts=total_drafts)


@app.route("/blog/new", methods=['GET', 'POST'])
@roles_required('editor')
def blog_new_post():
	g.breadcrumbs = []
	g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
	g.breadcrumbs.append(Breadcrumb('/blog', 'Blog'))
	g.breadcrumbs.append(Breadcrumb('', 'New Article'))
	if request.method == 'POST':
		form = BlogPostForm(request.form)
		if form.validate():
			post = Post()
			post.title = form.title.data
			post.body = form.body.data
			post.meta_keywords = form.meta_keywords.data
			post.meta_description = form.meta_description.data
			post.thumbnail = form.thumbnail.data
			post.user_id = current_user.id
			db.session.add(post)
			db.session.commit()
			flash('Post created successfully. You can continue editing or return to Article List.', 'success')
			return redirect(url_for('blog_edit_post', slug=post.slug))
		else:
			flash('There are errors on the form. Please fix them before continuing.', 'error')
	else:
		form = BlogPostForm()
	return render_template('blog_edit.html', form=form, post=None)

@app.route("/blog/bb/preview", methods=['POST'])
@roles_required('editor')
def blog_preview_post():
	body = request.form['data']
	return render_template('blog_bb_preview.html', body=bbcode_parser.format(body))

@app.route("/blog/<string:slug>/edit/", methods=['GET', 'POST'])
@roles_required('editor')
def blog_edit_post(slug):
	post = Post.query.filter_by(slug=slug).first_or_404()
	g.breadcrumbs = []
	g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
	g.breadcrumbs.append(Breadcrumb('/blog', 'Blog'))
	g.breadcrumbs.append(Breadcrumb('', post.title))
	if post.user_id != current_user.id:
		abort(403)
	if request.method == 'POST':
		form = BlogPostForm(request.form)
		if form.validate():
			post.title = form.title.data
			post.body = form.body.data
			post.meta_keywords = form.meta_keywords.data
			post.meta_description = form.meta_description.data
			post.thumbnail = form.thumbnail.data
			if form.published.data == True and post.published_at == None:
				post.published_at = datetime.datetime.now()
			if form.published.data == False and post.published_at != None:
				post.published_at = None
			db.session.commit()
			if request.form['submit'] == 'Save & Exit':
				flash('Post updated successfully.', 'success')
				return redirect(url_for('top_slug', slug=post.slug))
			flash('Post updated successfully. You can continue editing or return to Article List.', 'success')
			return redirect(url_for('blog_edit_post', slug=post.slug))
		else:
			flash('There are errors on the form. Please fix them before continuing.', 'error')
	else:
		form = BlogPostForm(obj=post)
		if post.published_at != None:
			form.published.data = True
	return render_template('blog_edit.html', form=form, post=post)


# ------------ USER --------------------
@app.route("/user/<string:slug>")
def user_view(slug):
	user = User.query.options(undefer_group('full')).filter_by(slug=slug).first_or_404()
	g.breadcrumbs = []
	g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
	g.breadcrumbs.append(Breadcrumb('/community', 'Community'))
	g.breadcrumbs.append(Breadcrumb('', user.fullname()))
	return render_template('user_view.html', user=user)


@app.route("/user/<string:slug>/edit", methods=['GET', 'POST'])
@login_required
def user_edit(slug):
	user = User.query.filter_by(slug=slug).first_or_404()
	g.breadcrumbs = []
	g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
	g.breadcrumbs.append(Breadcrumb('/community', 'Community'))
	g.breadcrumbs.append(Breadcrumb('/user/'+slug, user.fullname()))
	g.breadcrumbs.append(Breadcrumb('', 'Edit My Profile'))
	if user.id != current_user.id:
		abort(403)
	if request.method == 'POST':
		form = UserForm(request.form)
		if form.validate():
			user.type = form.type.data
			user.geo_lat		= form.geo_lat.data
			user.geo_lng		= form.geo_lng.data
			user.geo_address	= form.geo_address.data
			if user.type == 'developer':
				if user.first_name != form.first_name.data or user.last_name != form.last_name.data:
					app.logger.debug('reset slug')
					user.slug = None
				user.first_name		= form.first_name.data
				user.last_name 		= form.last_name.data
				user.birthdate		= form.birthdate.data
				user.sfdc_start		= form.sfdc_start.data
				user.sfdc_skills	= form.sfdc_skills.data
				user.sfdc_certificates = form.sfdc_certificates.data
				user.other_skills	= form.other_skills.data
				user.google_plus	= form.google_plus.data
				user.linkedin		= form.linkedin.data
				user.facebook		= form.facebook.data
				user.personal_site	= form.personal_site.data
			elif user.type == 'company':
				if user.company_name != form.company_name.data:
					user.slug = None
				user.company_name	= form.company_name.data
				user.company_info	= form.company_info.data
				user.google_plus	= form.google_plus.data
				user.linkedin		= form.linkedin.data
				user.facebook		= form.facebook.data
				user.personal_site	= form.personal_site.data
			elif user.type == 'other':
				user.first_name		= form.first_name.data
				user.last_name 		= form.last_name.data
				user.birthdate		= form.birthdate.data
				user.about_myself	= form.about_myself.data
			db.session.commit()
			flash('Profile updated successfully', 'success')
			return redirect(url_for('user_view', slug=user.slug))
		else:
			flash('There are errors on the form. Please fix them before continuing.', 'error')
	else:
		form = UserForm(obj=user)
	return render_template('user_edit.html', form=form, user=user)


# ------------ ACCOUNT SETTINGS ---------
@app.route('/account/settings', methods=['GET', 'POST'])
@login_required
def account_settings():
	user = current_user
	g.breadcrumbs = []
	g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
	g.breadcrumbs.append(Breadcrumb('/community', 'Community'))
	g.breadcrumbs.append(Breadcrumb('/user/'+user.slug, user.fullname()))
	g.breadcrumbs.append(Breadcrumb('', 'Account Settings'))
	if request.method == 'POST':
		form = SettingsForm(request.form)
		r = request
		if form.validate():
			user.gravatar = True if form.avatar_type.data == 'gravatar' else False

			if form.new_password.data:
				if form.new_password.data != form.old_password.data:
					if verify_password(form.old_password.data, user.password):
						user.password = encrypt_password(form.new_password.data)
					else:
						form.old_password.errors.append('Wrong old password')
				else:
					form.new_password.errors.append('Old and New passwords are the same')

			file = request.files['avatar_file']
			file_error = False
			if file:
				filename = 'avatar_'+str(current_user.id+1024)
				file_ext = imghdr.what(file)
				if file_ext in ALLOWED_EXTENSIONS:
					full_filename = filename+'.'+file_ext
					size = (200, 200)
					img = Image.open(file)
					width, height = img.size
					if width > height:
						delta = width - height
						left = int(delta/2)
						upper = 0
						right = height + left
						lower = height
					else:
						delta = height - width
						left = 0
						upper = int(delta/2)
						right = width
						lower = width + upper
					img = img.crop((left, upper, right, lower))
					img.thumbnail(size, Image.ANTIALIAS)
					img.save(os.path.join(app.config['AVATAR_FOLDER'], full_filename), quality=90, dpi=(72,72))
					user.avatar_link = full_filename
				else:
					form.avatar_file.errors.append('File type is not allowed.')
					flash('There are errors on the form. Please fix them before continuing.', 'error')
					file_error = True
			if file_error == False:
				db.session.commit()
				flash('Settings updated successfully.', 'success')
		else:
			flash('There are errors on the form. Please fix them before continuing.', 'error')
	else:
		form = SettingsForm()
		form.avatar_type.data = 'gravatar' if user.gravatar == True else 'avatar'
		form.username.data = user.username
		form.email.data = user.email
		form.timezone.data = user.timezone
	return render_template('settings.html', form=form, user=user, rnd=int(random.random()*1000))


# ------------ FORUM --------------------
@app.route('/forum')
def forum_list():
	g.breadcrumbs = []
	g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
	g.breadcrumbs.append(Breadcrumb('/forum', 'Forums'))
	forums = Forum.query.order_by('id').all()
	return render_template('forum_list.html', forums=forums)


@app.route('/forum/<string:slug>')
@app.route("/forum/<string:slug>/page/<int:page>")
def forum_view(slug, page=1):
	forum = Forum.query.filter_by(slug=slug).first_or_404()
	g.breadcrumbs = []
	g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
	g.breadcrumbs.append(Breadcrumb('/forum', 'Forums'))
	g.breadcrumbs.append(Breadcrumb('/forum/'+forum.slug, forum.title))
	topics = ForumTopic.query.filter_by(forum_id=forum.id).\
					order_by(ForumTopic.created_at.desc()).\
					paginate(page, 20, True)
	return render_template('forum_view.html', forum=forum, topics=topics)


@app.route('/forum/action/new-topic/<string:forum_slug>', methods=['GET'])
@login_required
def forum_new_topic(forum_slug):
	forum = Forum.query.filter_by(slug=forum_slug).first_or_404()
	g.breadcrumbs = []
	g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
	g.breadcrumbs.append(Breadcrumb('/forum', 'Forums'))
	g.breadcrumbs.append(Breadcrumb('/forum/'+forum.slug, forum.title))
	g.breadcrumbs.append(Breadcrumb('', 'New Topic'))
	topic = ForumTopic()
	return render_template('topic_view.html', forum=forum, topic=topic, new_topic=True)


@app.route('/forum/action/new-topic/<string:forum_slug>', methods=['POST'])
@login_required
def forum_create_topic(forum_slug=None):
	body = request.form['body']
	return 'ZZZZZ'

@app.route('/forum/action/save-topic/<string:topic_slug>', methods=['POST'])
@login_required
def forum_save_topic(topic_slug):
	topic = ForumTopic.query.filter_by(slug=topic_slug).first_or_404()
	if topic.user_id != current_user.id:
		abort(403)
	r = request
	form = ForumTopicForm(obj=request.json)
	if form.validate():
		topic.title = form.title.data
		topic.body = form.body.data
		ForumTopicService.update(topic)
		return jsonify(status='ok', title=topic.title, body=topic.body, body_html=topic.body_html, slug=topic.slug)
	return jsonify(status='error', errors=form.errors), 400


@app.route('/forum/action/new-post/<string:topic_slug>', methods=['POST'])
@login_required
def forum_new_post(topic_slug=None):
	pass

@app.route('/forum/action/save-post/<int:post_id>', methods=['POST'])
@login_required
def forum_save_post(post_id=None):
	pass


# ------------ COMMUNITY ----------------
@app.route('/community')
def community_map():
	g.breadcrumbs = []
	g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
	g.breadcrumbs.append(Breadcrumb('/community', 'Community'))
	g.breadcrumbs.append(Breadcrumb('', 'Map'))
	return render_template('community_map.html')


@app.route('/community/list')
def community_list():
	g.breadcrumbs = []
	g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
	g.breadcrumbs.append(Breadcrumb('/community', 'Community'))
	g.breadcrumbs.append(Breadcrumb('', 'List'))
	return render_template('community_list.html')


# ------------ GET by SLUG --------------
@app.route('/<string:slug>')
def top_slug(slug):
	post = Post.query.filter(Post.slug==slug).first()
	if post:
		if post.published_at is None and post.user_id != current_user.id:
			abort(404)
		g.breadcrumbs = []
		g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
		g.breadcrumbs.append(Breadcrumb('/blog', 'Blog'))
		g.breadcrumbs.append(Breadcrumb('', post.title))
		if post.published_at is None:
			flash('This post is not published. Only you can see it.', 'warning')
		meta = Meta(title=post.title+' | Salesforce-Developer.NET',
				description=post.meta_description,
				keywords=post.meta_description
				)
		return render_template('blog_view.html', post=post, meta=meta)
	topic = ForumTopic.query.filter(ForumTopic.slug==slug).first()
	if topic:
		g.breadcrumbs = []
		g.breadcrumbs.append(Breadcrumb('/', 'Salesforce-developer.net'))
		g.breadcrumbs.append(Breadcrumb('/forum', 'Forums'))
		g.breadcrumbs.append(Breadcrumb('/forum/'+topic.forum.slug, topic.forum.title))
		g.breadcrumbs.append(Breadcrumb('', topic.title))
		posts = ForumPost.query.filter_by(topic_id=topic.id).order_by(ForumPost.created_at.desc())
		meta = Meta(title=topic.title+' | Salesforce-Developer.NET',
				description=topic.title,
				keywords=topic.forum.title)
		return render_template('topic_view.html', topic=topic, posts=posts, meta=meta)
	abort(404)

# ------------ ERROR HANDLERS ----------
@app.errorhandler(404)
def page_not_found(e):
	flash('Requested resource not found.', 'error')
	if request.mimetype == 'application/json':
		return 'Requested resource not found.', 404
	return render_template('error.html'), 404

@app.errorhandler(403)
def no_permissions(e):
	flash('You don\'t have the permission to access the requested resource', 'error')
	if request.mimetype == 'application/json':
		return 'You don\'t have the permission to access the requested resource', 403
	return render_template('error.html'), 403