# encoding: utf-8

from flask import render_template
import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckan.logic as logic



class BaseController:


    def load_admin_view():

        context = {'model': model,
                   'user': toolkit.g.user, 'auth_user_obj': toolkit.g.userobj}
        try:
            logic.check_access('sysadmin', context, {})
        except logic.NotAuthorized:
            toolkit.abort(403, 'Need to be system administrator to administer')

        return render_template('admin_panel.html')