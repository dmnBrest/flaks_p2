# -*- coding: utf-8 -*-

from flask_wtf import Form
import pytz

from wtforms import StringField, TextAreaField, BooleanField, SelectField, DateField, FloatField, \
					RadioField, validators, PasswordField
from flask_wtf.file import FileField, FileAllowed


class BlogPostForm(Form):
	title 				= StringField('Title', [validators.DataRequired(), validators.Length(min=8, max=255)])
	body 				= TextAreaField('Body', [validators.length(min=10, max=200)])
	thumbnail			= StringField('Thumbnail', [validators.length(max=255)])
	meta_keywords 		= StringField('Keywords', [validators.length(max=255)])
	meta_description 	= StringField('Description', [validators.length(max=255)])
	published			= BooleanField('Published')


class UserForm(Form):
	first_name 			= StringField('First name', [validators.Length(min=2, max=255), validators.Optional(), validators.Regexp(regex=r'^[\w-]+$', message='Value is too complicated.')])
	last_name 			= StringField('First name', [validators.Length(min=2, max=255), validators.Optional(), validators.Regexp(regex=r'^[\w-]+$', message='Value is too complicated.')])
	type				= SelectField('I\'m', choices=[(None, '- select -'), ('developer', 'Developer'), ('company', 'Company'), ('other', 'Other')], description='Developer, Company, Other')
	birthdate			= DateField('Birthdate', [validators.Optional()], format='%m/%d/%Y', description='mm/dd/yyyy')
	google_plus			= StringField('Google+', [validators.Optional(), validators.Regexp(regex=r'^https://plus.google.com/', message='URL is not valid')], description='ex.: https://plus.google.com/103521493967721088420')
	linkedin			= StringField('LinkedIn', [validators.Optional(), validators.Regexp(regex=r'^https://www.linkedin.com/', message='URL is not valid')], description='ex.: https://www.linkedin.com/in/dmitryshnyrevsalesforcedev/')
	facebook			= StringField('Facebook', [validators.Optional(), validators.Regexp(regex=r'^https://www.facebook.com/', message='URL is not valid')], description='ex.: https://www.facebook.com/dmitry.shnyrev.salesforce.developer')
	personal_site		= StringField('Personal Site', [validators.Optional(), validators.URL(message='URL is not valid')], description='ex.: http://salesforce-developer.ru')
	geo_lat				= FloatField('Latitude', validators=[validators.Optional()])
	geo_lng				= FloatField('Longitude', validators=[validators.Optional()])
	geo_address			= StringField('Address')
	sfdc_start			= SelectField('Start working with Salesforce from', choices=[('', ''), ('2014', '2014'), ('2013', '2013'), ('2012', '2012'), ('2011', '2011'), ('2010', '2010'), ('2009', '2009')], validators=[validators.Optional()])
	sfdc_skills			= TextAreaField('Salesforce Skills', [validators.length(max=2048)])
	sfdc_certificates	= TextAreaField('Certificates', [validators.length(max=1024)], description='ex.: Salesforce certified developer - DEV 401 (January 2012)')
	other_skills		= TextAreaField('Other Skills', [validators.length(max=2048)], description='ex.: PHP, Python, Java, and others. Short description.')
	company_name		= StringField('Company Name', [validators.Optional(), validators.Length(min=2, max=255), validators.Regexp(regex=r'^[\w\-&]+$', message='Value is too complicated.')])
	company_info		= TextAreaField('About Company', [validators.length(max=2048)])
	about_myself		= TextAreaField('About Myself', [validators.length(max=2048)])

	def validate(self):
		success = True
		if not super(UserForm, self).validate():
			success = False
		if self.type.data == 'company' and not self.company_name.data:
			self.company_name.errors.append("Company name is required.")
			success = False
		return success

class SettingsForm(Form):
	avatar_type				= RadioField('Avatar Type', choices=[('gravatar', 'Gravatar.com'), ('avatar', 'Internal avatar')])
	avatar_file				= FileField('File to Upload', validators=[FileAllowed(['jpg', 'png'], 'Images only!')])
	email					= StringField('Email', [validators.Email(), validators.length(max=255)])
	username				= StringField('Username', [validators.DataRequired(message='Username not provided'),
														validators.Length(min=4, max=25),
														validators.Regexp('^[a-zA-Z0-9_-]+$',  message='Wrong Username format. "a-z", "A-Z", "0-9", "_" and "-" characters are allowed. Min 4 characters.')])
	timezone				= SelectField('Timezone', choices=[(val, val) for val in pytz.common_timezones])
	old_password			= PasswordField('Current Password', [validators.length(max=255)])
	new_password			= PasswordField('New Password', [validators.length(max=255)])


class ForumTopicForm(Form):
	title	= StringField('Title', [validators.DataRequired(), validators.Length(min=5, max=255)])
	body	= TextAreaField('Body', [validators.length(min=4, max=2048)])


class ForumPostForm(Form):
	body	= TextAreaField('Body', [validators.length(min=4, max=2048)])