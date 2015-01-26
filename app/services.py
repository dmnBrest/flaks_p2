# -*- coding: utf-8 -*-

from app import app, db, bbcode_parser
from models import User, Picture, Post, Forum, ForumTopic, ForumPost, PostHistory, ForumPostHistory, ForumTopicHistory
from slugify import slugify
from sqlalchemy.orm.attributes import get_history
import pygeoip, os
import re


class PostService(object):
	@classmethod
	def insert(cls, post):
		post = PostService._upsert(post)
		post.version = 0
		db.session.add(post)
		db.session.commit()
		return post
	@classmethod
	def update(cls, post):
		post = PostService._upsert(post)
		post_history = PostHistory()
		post_history.version = post.version
		post.version += 1
		#save post copy
		post_history.title = attr_old_value(post, 'title')
		post_history.body = attr_old_value(post, 'body')
		post_history.meta_keywords = attr_old_value(post, 'meta_keywords')
		post_history.meta_description = attr_old_value(post, 'meta_description')
		post_history.post_id = post.id
		db.session.add(post)
		db.session.add(post_history)
		db.session.commit()
		return post
	@classmethod
	def _upsert(cls, post):
		parts = post.body.split("[more]")
		post.preview_html = smile_it(bbcode_parser.format(parts[0].strip()))
		if len(parts) > 1:
			post.body_html = smile_it(bbcode_parser.format(parts[1].strip()))
		else:
			post.body_html = None
		if post.slug is None:
			ttitle = post.title
			if ttitle.startswith('topic'):
				ttitle = 'blog-'+ttitle
			post.slug = safe_slugify(Post, post, ttitle)
		return post


class CommentService(object):
	@classmethod
	def insert(cls, comment):
		comment.body_html = smile_it(bbcode_parser.format(comment.body.strip()))
		comment.version = 0
		db.session.add(comment)
		db.session.commit()
		return comment
	@classmethod
	def update(cls, comment):
		comment.body_html = smile_it(bbcode_parser.format(comment.body.strip()))
		db.session.add(comment)
		db.session.commit()
		return comment


class ForumService(object):
	@classmethod
	def insert(cls, forum):
		forum.slug = safe_slugify(Forum, forum, forum.title)
		db.session.add(forum)
		db.session.commit()


class ForumTopicService(object):
	@classmethod
	def insert(cls, topic):
		topic.body_html = smile_it(bbcode_parser.format(topic.body.strip()))
		topic.slug = safe_slugify(ForumTopic, topic, 'topic-'+topic.title)
		topic.version = 0
		db.session.add(topic)
		db.session.commit()
		forum = topic.forum
		forum.total_topics = (forum.total_topics or 0) + 1
		db.session.add(forum)
		db.session.commit()
		return topic
	@classmethod
	def update(cls, topic):
		topic.body_html = smile_it(bbcode_parser.format(topic.body.strip()))
		if topic.slug is None:
			topic.slug = safe_slugify(ForumTopic, topic, 'topic-'+topic.title)
		topic_history = ForumTopicHistory()
		topic_history.version = topic.version
		topic.version += 1
		topic_history.title = attr_old_value(topic, 'title')
		topic_history.body = attr_old_value(topic, 'body')
		db.session.add(topic)
		db.session.add(topic_history)
		db.session.commit()
		return topic


class ForumPostService(object):
	@classmethod
	def insert(cls, post):
		post.body_html = smile_it(bbcode_parser.format(post.body.strip()))
		post.version = 0
		db.session.add(post)
		db.session.commit()
		topic = post.topic
		topic.last_post_id = post.id
		topic.total_posts = (topic.total_posts or 0) + 1
		db.session.add(topic)
		forum = post.forum
		forum.last_post_id = post.id
		db.session.add(forum)
		db.session.commit()
		return post
	@classmethod
	def update(cls, post):
		post.body_html = smile_it(bbcode_parser.format(post.body.strip()))
		post_history = ForumTopicHistory()
		post_history.version = post.version
		post.version += 1
		post_history.body = attr_old_value(post, 'body')
		db.session.add(post)
		db.session.add(post_history)
		db.session.commit()
		return post

# ---------- HELPERS ---------------
basedir = os.path.abspath(os.path.dirname(__file__))
rawdata = pygeoip.GeoIP(os.path.join(basedir, '../GeoLiteCity.dat'))
def ipquery(ip):
	data = rawdata.record_by_name(ip)
	return data

def safe_slugify(cls, obj, text):
	slug = slugify(text)
	slug_result = slug
	i = 1
	while True:
		obj = db.session.query(cls).filter(cls.slug==slug_result, cls.id != obj.id).first()
		if obj is None:
			return slug_result
		slug_result = slug+'_'+str(i)
		i += 1

bb_smiles = {
	#'8)': 'glasses.png',
	':D': 'emoticon-happy.png',
	':(': 'emoticon-unhappy.png',
	':O': 'emoticon-surprised.png',
	':)': 'emoticon-smile.png',
	':P': 'emoticon-tongue.png',
	';)': 'emoticon-wink.png'
}

def smile_it(str):
	#str = str.replace(smile, '<img src="/static/markitup/images/%s" alt="smile" />'%url)
	for smile, name in bb_smiles.items():
		str = re.sub(re.compile(re.escape(smile)+'(\s)', flags=re.IGNORECASE), '<img src="/static/markitup/images/%s" alt="smile" />\\1'%name, str)
		str = re.sub(re.compile(re.escape(smile)+'<', flags=re.IGNORECASE), '<img src="/static/markitup/images/%s" alt="smile" /><'%name, str)
		str = re.sub(re.compile(re.escape(smile)+'$', flags=re.IGNORECASE), '<img src="/static/markitup/images/%s" alt="smile" />'%name, str)
	return str

def attr_old_value(obj, a_name):
	a, u, d = get_history(obj, a_name)
	attr = None
	if d:
		attr = d[0]
	elif u:
		attr = u[0]
	else:
		attr = a[0]
	return attr