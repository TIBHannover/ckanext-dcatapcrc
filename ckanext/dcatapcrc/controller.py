# encoding: utf-8

from flask import render_template
import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckan.logic as logic
from ckan.model import Package
import json
import requests
from ckanext.dcat.processors import RDFSerializer
from rdflib import Graph
from io import StringIO
from xml.etree import ElementTree


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


        ElementTree.register_namespace("dc", "http://purl.org/dc/terms/")
        ElementTree.register_namespace("dcat", "http://www.w3.org/ns/dcat#")
        ElementTree.register_namespace("foaf", "http://xmlns.com/foaf/0.1/")
        ElementTree.register_namespace("SCHEMAORG", "https://schema.org/")
        ElementTree.register_namespace("EMMO", "http://emmo.info/emmo/")
        ElementTree.register_namespace("TEMA", "https://www.tib.eu/tema/")
        ElementTree.register_namespace("ENVO", "http://purl.obolibrary.org/obo/envo/")
        ElementTree.register_namespace("NCIT", "http://purl.obolibrary.org/obo/ncit/")
        xml = ElementTree.fromstring("<RDF></RDF>")
        
        for dataset in all_datasets:
            if dataset.state == 'active':                
                package = toolkit.get_action('package_show')({}, {'name_or_id': dataset.name})                
                serializer = RDFSerializer(profiles=package.get('profiles'))
                rdf_output = serializer.serialize_dataset(package)                                
                # print(ElementTree.fromstring(rdf_output.decode('utf-8'))[0].tag)
                childNodeList = ElementTree.fromstring(rdf_output.decode('utf-8'))
                for node in childNodeList: 
                    xml.append(node)
        
        xmlstr = ElementTree.tostring(xml, encoding='utf8', method='xml')
        from flask import make_response
        response = make_response(xmlstr)
        response.headers['Content-type'] = "application/rdf+xml"
        return response