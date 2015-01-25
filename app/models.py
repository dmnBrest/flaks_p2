# -*- coding: utf-8 -*-

import os
from app import app, db, bbcode_parser
from flask import g
from flask.ext.security import UserMixin, RoleMixin
from sqlalchemy.orm import MapperExtension, deferred
from sqlalchemy import event
import urllib, hashlib
from datetime import datetime

# -------- AUDIT ----------------

class AuditExtension(MapperExtension):
	def before_insert(self, mapper, connection, instance):
		""" Make sure the audit fields are set correctly  """
		instance.created_at = datetime.utcnow()
		instance.created_by = g.identity.id if hasattr(g, 'identity') else None
		instance.updated_at = datetime.utcnow()
		instance.updated_by = g.identity.id if hasattr(g, 'identity') else None
	def before_update(self, mapper, connection, instance):
		""" Make sure when we update this record the created fields stay unchanged!  """
		instance.created_at = instance.created_at
		instance.created_by = instance.created_by
		instance.updated_at = datetime.utcnow()
		instance.updated_by = g.identity.id if hasattr(g, 'identity') else None


# -------- ROLE -----------------
roles_users = db.Table('roles_users',
		db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
		db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
	id 					= db.Column(db.Integer(), primary_key=True)
	name 				= db.Column(db.String(80), unique=True)
	description 		= db.Column(db.String(255))


# --------- USER ----------------
class User(db.Model, UserMixin):
	id 					= db.Column(db.Integer, primary_key=True)
	username			= db.Column(db.String(255), unique=True)
	slug				= db.Column(db.String(255), unique=True)
	email 				= db.Column(db.String(255), unique=True)
	first_name			= db.Column(db.String(255))
	last_name			= db.Column(db.String(255))
	type				= db.Column(db.String(255))  # 'developer', 'company', 'other'
	birthdate			= deferred(db.Column(db.Date), group='full')
	gravatar			= db.Column(db.Boolean)
	avatar_link			= db.Column(db.String(255))
	google_plus			= deferred(db.Column(db.String(255)), group='full')
	linkedin			= deferred(db.Column(db.String(255)), group='full')
	facebook			= deferred(db.Column(db.String(255)), group='full')
	personal_site		= deferred(db.Column(db.String(255)), group='full')
	geo_manual			= deferred(db.Column(db.Boolean), group='full')
	geo_lat				= deferred(db.Column(db.Float(Precision=64)), group='full')
	geo_lng				= deferred(db.Column(db.Float(Precision=64)), group='full')
	geo_address			= deferred(db.Column(db.String(255)), group='full')
	sfdc_start			= deferred(db.Column(db.Integer), group='full')
	sfdc_skills			= deferred(db.Column(db.Text), group='full')
	sfdc_certificates	= deferred(db.Column(db.Text), group='full')
	other_skills		= deferred(db.Column(db.Text), group='full')
	company_name		= db.Column(db.String(255))
	company_info		= deferred(db.Column(db.Text), group='full')
	about_myself		= deferred(db.Column(db.Text), group='full')
	password 			= deferred(db.Column(db.String(255)), group='system')
	active 				= deferred(db.Column(db.Boolean()), group='system')
	confirmed_at 		= deferred(db.Column(db.DateTime()), group='system')
	last_login_at 		= deferred(db.Column(db.DateTime()), group='system')
	current_login_at 	= deferred(db.Column(db.DateTime()), group='system')
	last_login_ip 		= deferred(db.Column(db.String(255)), group='system')
	current_login_ip 	= deferred(db.Column(db.String(255)), group='system')
	login_count 		= deferred(db.Column(db.Integer), group='system')
	timezone			= deferred(db.Column(db.String(255)), group='system')

	created_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	created_by 			= db.Column(db.Integer())
	updated_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
	updated_by			= db.Column(db.Integer())
	__mapper_args__ = {'extension': AuditExtension()}

	roles 				= db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))

	def __repr__(self):
		return '<User %r>' % self.username
	def fullname(self):
		if self.type == 'company' and self.company_name != None:
			return self.company_name
		elif self.first_name or self.last_name:
			ff = (self.first_name or '')+' '+(self.last_name or '')
			return ff.strip()
		return self.username
	def get_gravatar_link(self, size):
		default = "https://salesforce-developer.ru/wp-content/uploads/avatars/no-avatar.jpg"
		gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(self.email.lower()).hexdigest() + "?"
		gravatar_url += urllib.urlencode({'d':default, 's':str(size or 64)})
		return gravatar_url
	def get_internal_avatar_link(self, size):
		if self.avatar_link != None and self.avatar_link != '':
			return '/pictures/avatars/'+self.avatar_link
		return '/static/default-avatar.png'
	def get_avatar(self, size):
		if self.gravatar == True:
			return self.get_gravatar_link(size)
		else:
			return self.get_internal_avatar_link(size)

@event.listens_for(User, 'before_insert')
def before_insert_user(mapper, connection, target):
	target.slug = safe_slugify(User, target, target.fullname())
	target.gravatar = True

@event.listens_for(User, 'before_update')
def before_update_user(mapper, connection, target):
	if target.slug == None:
		target.slug = safe_slugify(User, target, target.fullname())
	if target.geo_lat == None or target.geo_lng == None:
		if target.current_login_ip != None:
			ip_data = ipquery(target.current_login_ip)
			if ip_data:
				target.geo_lat = ip_data['latitude']
				target.geo_lng = ip_data['longitude']
				target.timezone = ip_data['time_zone']
				if ip_data['city']:
					target.geo_address = ip_data['city']+', '+ip_data['country_name']
				else:
					target.geo_address = ip_data['country_name']


# --------- PICTURE -----------------
class Picture(db.Model):
	id					= db.Column(db.Integer(), primary_key=True)
	filename			= db.Column(db.String(255))
	user_id				= db.Column(db.Integer, db.ForeignKey('user.id'))
	user 				= db.relationship("User")

	created_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	created_by 			= db.Column(db.Integer())
	updated_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
	updated_by 			= db.Column(db.Integer())
	__mapper_args__ = {'extension': AuditExtension()}

	def full_filename(self):
		return os.path.join(app.config['UPLOAD_FOLDER'], self.filename)
	def full_thumb_filename(self, size):
		return os.path.join(app.config['UPLOAD_FOLDER'], 'thumb'+str(size)+'_'+self.filename)
	def picture_path(self):
		return '/pictures/'+self.filename
	def thumb_path(self, size):
		return '/pictures/thumbs/thumb'+str(size)+'_'+self.filename

@event.listens_for(Picture, 'before_delete')
def before_delete_picture(mapper, connection, target):
	os.remove(target.full_filename())
	os.remove(target.full_thumb_filename(256))


# --------- POST ----------------------
class Post(db.Model):
	id					= db.Column(db.Integer, primary_key=True)
	slug				= db.Column(db.String(255), unique=True, nullable=False)
	title				= db.Column(db.String(255), nullable=False)
	thumbnail			= db.Column(db.String(255))
	type				= db.Column(db.String(255))
	body				= db.Column(db.Text)
	preview_html		= db.Column(db.Text)
	body_html			= db.Column(db.Text)
	meta_keywords		= db.Column(db.Text)
	meta_description	= db.Column(db.Text)
	user_id				= db.Column(db.Integer, db.ForeignKey('user.id'))
	user 				= db.relationship("User")
	published_at 		= db.Column(db.DateTime)
	version				= db.Column(db.Integer)

	created_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	created_by 			= db.Column(db.Integer)
	updated_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
	updated_by 			= db.Column(db.Integer)
	__mapper_args__ = {'extension': AuditExtension()}

class PostHistory(db.Model):
	id					= db.Column(db.Integer, primary_key=True)
	title				= db.Column(db.String(255), nullable=False)
	body				= db.Column(db.Text)
	meta_keywords		= db.Column(db.Text)
	meta_description	= db.Column(db.Text)
	version				= db.Column(db.Integer)
	post_id				= db.Column(db.Integer, db.ForeignKey('post.id'))
	post 				= db.relationship("Post")

	created_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	created_by 			= db.Column(db.Integer)
	updated_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
	updated_by 			= db.Column(db.Integer)
	__mapper_args__ = {'extension': AuditExtension()}


class Comment(db.Model):
	id					= db.Column(db.Integer, primary_key=True)
	body				= db.Column(db.Text)
	body_html			= db.Column(db.Text)
	post_id				= db.Column(db.Integer, db.ForeignKey('post.id'))
	post 				= db.relationship("Post")
	user_id				= db.Column(db.Integer, db.ForeignKey('user.id'))
	user 				= db.relationship("User")
	version				= db.Column(db.Integer)

	created_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	created_by 			= db.Column(db.Integer)
	updated_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
	updated_by 			= db.Column(db.Integer)
	__mapper_args__ = {'extension': AuditExtension()}

class CommentHistory(db.Model):
	id					= db.Column(db.Integer, primary_key=True)
	body				= db.Column(db.Text)
	version				= db.Column(db.Integer)
	comment_id			= db.Column(db.Integer, db.ForeignKey('comment.id'))
	comment 			= db.relationship("Comment")

	created_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	created_by 			= db.Column(db.Integer)
	updated_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
	updated_by 			= db.Column(db.Integer)
	__mapper_args__ = {'extension': AuditExtension()}

class Forum(db.Model):
	id					= db.Column(db.Integer, primary_key=True)
	slug				= db.Column(db.String(255), unique=True, nullable=False)
	title				= db.Column(db.String(255), nullable=False)
	description			= db.Column(db.Text)
	total_topics		= db.Column(db.Integer)
	last_post_id		= db.Column(db.Integer, db.ForeignKey('forum_post.id', use_alter=True, name='fk_forum_post_id'))
	last_post			= db.relationship("ForumPost", foreign_keys=[last_post_id])

	created_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	created_by 			= db.Column(db.Integer)
	updated_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
	updated_by 			= db.Column(db.Integer)
	__mapper_args__ = {'extension': AuditExtension()}


class ForumTopic(db.Model):
	id					= db.Column(db.Integer, primary_key=True)
	slug				= db.Column(db.String(255), unique=True, nullable=False)
	title				= db.Column(db.String(255), nullable=False)
	body				= db.Column(db.Text)
	body_html			= db.Column(db.Text)
	total_posts			= db.Column(db.Integer)
	last_post_id		= db.Column(db.Integer, db.ForeignKey('forum_post.id', use_alter=True, name='fk_topic_post_id'))
	last_post			= db.relationship("ForumPost", foreign_keys=[last_post_id])
	user_id				= db.Column(db.Integer, db.ForeignKey('user.id'))
	user 				= db.relationship("User")
	forum_id			= db.Column(db.Integer, db.ForeignKey('forum.id'))
	forum 				= db.relationship("Forum")
	version				= db.Column(db.Integer)

	created_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	created_by 			= db.Column(db.Integer)
	updated_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
	updated_by 			= db.Column(db.Integer)
	__mapper_args__ = {'extension': AuditExtension()}


class ForumTopicHistory(db.Model):
	id					= db.Column(db.Integer, primary_key=True)
	title				= db.Column(db.String(255), nullable=False)
	body				= db.Column(db.Text)
	forum_topic_id		= db.Column(db.Integer, db.ForeignKey('forum_topic.id'))
	forum_topic 		= db.relationship("ForumTopic")
	version				= db.Column(db.Integer)

	created_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	created_by 			= db.Column(db.Integer)
	updated_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
	updated_by 			= db.Column(db.Integer)
	__mapper_args__ = {'extension': AuditExtension()}

class ForumPost(db.Model):
	id					= db.Column(db.Integer, primary_key=True)
	body				= db.Column(db.Text)
	body_html			= db.Column(db.Text)
	user_id				= db.Column(db.Integer, db.ForeignKey('user.id'))
	user 				= db.relationship("User")
	forum_id			= db.Column(db.Integer, db.ForeignKey('forum.id'))
	forum				= db.relationship("Forum", foreign_keys=[forum_id])
	topic_id			= db.Column(db.Integer, db.ForeignKey('forum_topic.id'))
	topic				= db.relationship("ForumTopic", foreign_keys=[topic_id])
	version				= db.Column(db.Integer)

	created_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	created_by 			= db.Column(db.Integer)
	updated_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
	updated_by 			= db.Column(db.Integer)
	__mapper_args__ = {'extension': AuditExtension()}


class ForumPostHistory(db.Model):
	id					= db.Column(db.Integer, primary_key=True)
	body				= db.Column(db.Text)
	forum_post_id		= db.Column(db.Integer, db.ForeignKey('forum_post.id'))
	forum_post 			= db.relationship("ForumPost")
	version				= db.Column(db.Integer)

	created_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	created_by 			= db.Column(db.Integer)
	updated_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
	updated_by 			= db.Column(db.Integer)
	__mapper_args__ = {'extension': AuditExtension()}


class Vote(db.Model):
	id					= db.Column(db.Integer, primary_key=True)
	user_id				= db.Column(db.Integer, db.ForeignKey('user.id'))
	user 				= db.relationship("User")
	forum_topic_id		= db.Column(db.Integer, db.ForeignKey('forum_topic.id'))
	forum_topic			= db.relationship("ForumTopic")
	forum_post_id		= db.Column(db.Integer, db.ForeignKey('forum_post.id'))
	forum_post			= db.relationship("ForumPost")
	comment_id			= db.Column(db.Integer, db.ForeignKey('comment.id'))
	comment 			= db.relationship("Comment")
	type				= db.Column(db.String(255))           # '+1','-1'

	created_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	created_by 			= db.Column(db.Integer)
	updated_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
	updated_by 			= db.Column(db.Integer)
	__mapper_args__ = {'extension': AuditExtension()}


class Message(db.Model):
	id					= db.Column(db.Integer, primary_key=True)
	body				= db.Column(db.Text)
	body_html			= db.Column(db.Text)
	parent_id			= db.Column(db.Integer, db.ForeignKey('message.id'))
	parent				= db.relationship("Message")
	from_id				= db.Column(db.Integer, db.ForeignKey('user.id'))
	form 				= db.relationship("User", foreign_keys=[from_id])
	to_id				= db.Column(db.Integer, db.ForeignKey('user.id'))
	to	 				= db.relationship("User", foreign_keys=[to_id])

	created_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	created_by 			= db.Column(db.Integer)
	updated_at 			= db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
	updated_by 			= db.Column(db.Integer)
	__mapper_args__ = {'extension': AuditExtension()}


# --------- Helpers ----------------------
from services import ipquery, safe_slugify

class Meta():
	def __init__(self, title=None, description=None, keywords=None):
		self.title = title or app.config['META_TITLE']
		self.description = description or app.config['META_DESCRIPTION']
		self.keywords = keywords or app.config['META_KEYWORDS']

class Breadcrumb():
	def __init__(self, url, title):
		self.url = url
		self.title = title




