#!/usr/bin/env python
import sys, string, xmlrpclib, re
from config import *

parentId_from = '52234383'
parentId_to = '64266803'
spaceKey_to = '~mscherbakov'

class WikiClient:
    
    def __init__(self, url, user, password):
        self.client = xmlrpclib.ServerProxy(url)
        self.token = self.client.confluence1.login(user, password)

    def execute(self, method, *args):
#        print "Executing %s.." % method
        return getattr(self.client.confluence1, method)(self.token, *args)

if __name__ == "__main__":
    wiki_from = WikiClient(WIKI_FROM_URL, WIKI_FROM_USER, WIKI_FROM_PASSWORD)
    wiki_to = WikiClient(WIKI_TO_URL, WIKI_TO_USER, WIKI_TO_PASSWORD)

    #Create an array with the only IDs of pages
    pages_from_ids = map (lambda page: page['id'], wiki_from.execute('getDescendents', parentId_from)) + [ parentId_from ]

    pages_to_info = []
    for id in pages_from_ids:
        page = wiki_from.execute('getPage', id)
        try:
            page_new = wiki_to.execute('getPage', spaceKey_to, page['title'])
        except xmlrpclib.Fault:  # In case if page doesn't exist in new place yet
            page_new = { 'space': spaceKey_to, 'title': page['title'] }

        page_new['content'] = page['content']
        print "Storing page with title '%s'.." % page_new['title']
        page_new = wiki_to.execute('storePage', page_new)
        
        # Save info for further moving pages
        pages_to_info += [ { 'id': page_new['id'], 'old_id': id, 'old_parent_id': page['parentId'] } ]

        for atch in wiki_from.execute('getAttachments', id):
            print "Processing attachment '%s'.." % atch['fileName'] 
            filedata = wiki_from.execute('getAttachmentData', id, atch['fileName'], '0')
            new_atch = { 'fileName': atch['fileName'], 'title': atch['title'], 'contentType': atch['contentType'], 'fileSize': atch['fileSize'], 'comment': '' }
            wiki_to.execute('addAttachment', page_new['id'], new_atch, filedata)
    
    print "Changing parents for %i uploaded pages..." % len(pages_to_info)
    for n in pages_to_info:
        if n['old_id'] != parentId_from:
            wiki_to.execute('movePage', n['id'], [ x for x in pages_to_info if x['old_id'] == n['old_parent_id'] ][0]['id'], 'append')
        else:
            wiki_to.execute('movePage', n['id'], parentId_to, 'append')  


