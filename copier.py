#!/usr/bin/env python
import sys, string, xmlrpclib, re
import config
from optparse import OptionParser

class WikiClient:
    
    def __init__(self, url, user, password):
        self.client = xmlrpclib.ServerProxy(url)
        self.token = self.client.confluence1.login(user, password)

    def execute(self, method, *args):
#        print "Executing %s.." % method
        return getattr(self.client.confluence1, method)(self.token, *args)

def get_opts():
    parser = OptionParser("Usage: %prog --id-from <id> --id-to <id_to> --spacekey-to <spaceKey>")
    parser.add_option('--id-from', dest='id_from', help='Parent Id of the page the copier should start reading from.')
    parser.add_option('--id-to', dest='id_to', help='Id of the page on target wiki, which will be the top of the pages hierarchy.')
    parser.add_option('--spacekey-to', dest='spacekey_to', help='Key of the target space')
    opts, args = parser.parse_args()
    if not (opts.id_to and opts.id_from and opts.spacekey_to):
        parser.error("Incorrect arguments.")
    return opts

if __name__ == "__main__":
    opts = get_opts()
    parentId_from = opts.id_from
    parentId_to = opts.id_to
    spaceKey_to = opts.spacekey_to
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


