# encoding: utf-8

from flask import render_template
import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckan.logic as logic
from ckan.model import Package
import json
import requests
from ckanext.dcat.processors import RDFSerializer



class BaseController:


    def load_admin_view():

        context = {'model': model,
                   'user': toolkit.g.user, 'auth_user_obj': toolkit.g.userobj}
        try:
            logic.check_access('sysadmin', context, {})
        except logic.NotAuthorized:
            toolkit.abort(403, 'Need to be system administrator to administer')

        return render_template('admin_panel.html')
    


    def export_catalog():

        context = {'model': model,
                   'user': toolkit.g.user, 'auth_user_obj': toolkit.g.userobj}
        try:
            logic.check_access('sysadmin', context, {})
        except logic.NotAuthorized:
            toolkit.abort(403, 'Need to be system administrator to administer')
        
        
        base_url = toolkit.config.get('ckan.site_url')
        ckan_root_path = toolkit.config.get('ckan.root_path')
        if not ckan_root_path:
            ckan_root_path = "/"
        all_datasets = Package.search_by_name('')
        catalog_endpoints = []
        for dataset in all_datasets:
            if dataset.state == 'active':
                catalog_endpoints.append(base_url + ckan_root_path + "dataset/" + dataset.name + ".rdf")
       
        package = toolkit.get_action('package_show')({}, {'name_or_id': all_datasets[0].name})
        response = toolkit.get_action('dcat_dataset_show')({}, {'id': package['id'],'format': 'rdf'})                
        datasets_rdf_format = []
        
        serializer = RDFSerializer(profiles=package.get('profiles'))
        rdf_output = serializer.serialize_dataset(package, _format=package.get('format'))

        # datasets_rdf_format.append(output)
                                

        # for url in catalog_endpoints:
            # res = requests.get(url, timeout=5, headers={"Authorization": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJFdnk4SWRSQnRqQ2VxbFdHTktaNlJ1UkJtcGswM25DMjUzUDZuVER4SFZwam1iZUJacl9qQVNQSjJNLUJZeVVPSFpVUmEwdFAwMGtCTnJ4RyIsImlhdCI6MTY3NDgyMjEwM30.BC3s6KOwbVa00fShoGkinxgBfVrRjAhQuNTgfN6YT2E"})
            # rdf_contents.append(res.content)
            # rdf_contents.append(ckan_to_dcat())
            # break


        # return json.dumps(datasets_rdf_format)
        from flask import make_response
        response = make_response(rdf_output)
        response.headers['Content-type'] = "application/rdf+xml"
        return response