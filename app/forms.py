# -*- coding: utf-8 -*-

from flask_wtf import Form
import pytz

from wtforms import StringField, TextAreaField, BooleanField, \
					SelectField, DateField, FloatField, \
					RadioField, validators, PasswordField
from flask_wtf.file import FileField, FileAllowed

class BlogPostForm(Form):
	title 				= StringField('Title', [validators.DataRequired(), validators.Length(min=20, max=255)])
	body 				= TextAreaField('Body', [validators.length(min=20, max=200)])
	thumbnail			= StringField('Thumbnail', [validators.length(max=255)])
	meta_keywords 		= StringField('Keywords', [validators.length(max=255)])
	meta_description 	= StringField('Description', [validators.length(max=255)])
	published			= BooleanField('Published')

class UserForm(Form):
	first_name 			= StringField('First name', [validators.length(max=255)])
	last_name 			= StringField('First name', [validators.length(max=255)])
	type				= SelectField('I\'m', choices=[('developer', 'Developer'), ('company', 'Company'), ('other', 'Other')], description='Developer, Company, Other')
	birthdate			= DateField('Birthdate', [validators.Optional()], format='%m/%d/%Y', description='mm/dd/yyyy')
	google_plus			= StringField('Google+', [validators.Optional(), validators.Regexp(regex=r'^https://plus.google.com/', message='URL is not valid')], description='ex.: https://plus.google.com/103521493967721088420')
	linkedin			= StringField('LinkedIn', [validators.Optional(), validators.Regexp(regex=r'^https://www.linkedin.com/', message='URL is not valid')], description='ex.: https://www.linkedin.com/in/dmitryshnyrevsalesforcedev/')
	facebook			= StringField('Facebook', [validators.Optional(), validators.Regexp(regex=r'^https://www.facebook.com/', message='URL is not valid')], description='ex.: https://www.facebook.com/dmitry.shnyrev.salesforce.developer')
	personal_site		= StringField('Personal Site', [validators.Optional(), validators.URL(message='URL is not valid')], description='ex.: http://salesforce-developer.ru')
	geo_lat				= FloatField('Latitude')
	geo_lng				= FloatField('Longitude')
	geo_address			= StringField('Address')
	sfdc_start			= SelectField('Start working with Salesforce from', choices=[('2014', '2014'), ('2013', '2013'), ('2012', '2012'), ('2011', '2011'), ('2010', '2010'), ('2009', '2009')])
	sfdc_skills			= TextAreaField('Salesforce Skills', [validators.length(max=2048)])
	sfdc_certificates	= TextAreaField('Certificates', [validators.length(max=1024)], description='ex.: Salesforce certified developer - DEV 401 (January 2012)')
	other_skills		= TextAreaField('Other Skills', [validators.length(max=2048)], description='ex.: PHP, Python, Java, and others. Short description.')
	company_name		= StringField('Company Name', [validators.length(max=255)])
	company_info		= TextAreaField('About Company', [validators.length(max=2048)])
	about_myself		= TextAreaField('About Myself', [validators.length(max=2048)])


class SettingsForm(Form):
	avatar_type				= RadioField('Avatar Type', choices=[('gravatar', 'Gravatar.com'), ('avatar', 'Internal avatar')])
	avatar_file				= FileField('File to Upload', validators=[FileAllowed(['jpg', 'png'], 'Images only!')])
	email					= StringField('Email', [validators.length(max=255)])
	username				= StringField('Username', [validators.length(max=255)])
	timezone				= SelectField('Timezone', choices=[(val, val) for val in pytz.common_timezones])
	old_password			= PasswordField('Current Password', [validators.length(max=255)])
	new_password			= PasswordField('New Password', [validators.length(max=255)])
