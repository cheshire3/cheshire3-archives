#
# Script:    eadEditingHandler.py
# Version:   0.02
# Date:      25 October 2010
# Copyright: &copy; University of Liverpool 2010
# Description:
#            Data creation and editing interface for EAD finding aids
#            - part of Cheshire for Archives v3
#
# Author(s): CS - Catherine Smith <catherine.smith@liverpool.ac.uk>
#
# Language:  Python
# Required externals:
#            cheshire3-base, cheshire3-sql, cheshire3-web
#            Py: localConfig.py, eadHandler.py
#            HTML: ead2002.html, edithelp.html, editmenu.html, header.html,
#                footer.html, ead-template.ssi
#            XSL: form.xsl, contents-editing.xsl, ead_order.xsl, reindent.xsl,
#                full.xsl, fullSplit.xsl
#            CSS: charkeyboard.css, contextmenu.css, form.css, form-ie.css,
#                struc-all.css, struc-ie.css, style.css, localStyles.css
#            Javascript: prototype.js (v 1.6.0), accesspoints.js,
#                collapsibleLists.js, cookies.js, contextmenu.js, form.js,
#                keyboard.js, tablednd.js                       
#            Images: c3_black.gif, valid-xhtml10, vcss, JISCcolour7.gif,
#                python-powered-w-70x28.png, right-mini.gif, winmin.png,
#                winmax.png, winmin-active.png, winmax-active.png,
#                winclose.png, winclose-active.png, CLon.gif,
#                whatisthissmall.gif, delete.png, delete-hover.png
#                            
# Version History: # left as example
# 0.01 - 20/01/2009 - CS - All functions for first release
# 0.02 - 25/10/2010 - JH - Bug fixes for v3.5.0
# 0.03 - 02/06/2011 - JH - Prevent reassign of builtin function 'list'
#
# --- Version History Truncated ---
# Version number will henceforth correspond to Cheshire3 for Archives release.
# Version history is delegated to source code repository.
#

import datetime
import glob
import codecs

from copy import deepcopy

from eadHandler import *

from cheshire3.record import LxmlRecord


class EadEditingHandler(EadHandler):
    global repository_name, repository_link, repository_logo, htmlPath
    templatePath = os.path.join(htmlPath, 'template.ssi')
    htmlTitle = None
    htmlNav = None
    logger = None
    errorFields = []
    required_xpaths_components = ['did/unitid',
                                  'did/unittitle',
                                  'did/unitdate']
    required_xpaths = [
        'did/unitid',
        'did/unittitle',
        'did/unitdate',
        'did/unitdate/@normal',
        'did/repository',
        'did/origination',
        'did/physdesc/extent',
        'did/langmaterial/language',
        'scopecontent',
        'accessrestrict'
    ]
    
    altrenderDict = {'surname': 'a',
                     'organisation': 'a',
                     'dates': 'y',
                     'other': 'x',
                     'loc': 'z'                    
                     }

# Dictionaries of punctuation
# One string means that it goes after the values two strings are either side
# first before second after
    
    persnamePunct = {'a': [u',\u00A0'],
                     'forename': [u'.\u00A0'],
                     'y': [u'(', u')\u00A0'],
                     'epithet': [u',\u00A0']
                     }
    
    famnamePunct = {'a': [u'\u00A0'],
                    'x': [u'.\u00A0'],
                    'title': [u'.\u00A0'],
                    'y': [u'(', u')\u00A0'],
                    'z': [u'.\u00A0']
                    }
    
    corpnamePunct = {'x': [u'\u00A0--\u00A0', u'\u00A0'],
                     'y': [u'(', u')\u00A0'],
                     'z': [u'\u00A0--\u00A0', u'\u00A0']                            
                     }
    
    subjectPunct = {'x': [u'\u00A0--\u00A0', u'\u00A0'],
                    'y': [u'\u00A0--\u00A0', u'\u00A0'],
                    'z': [u'\u00A0--\u00A0', u'\u00A0']                            
                    }
    
    geognamePunct = {'x': [u'\u00A0--\u00A0', u'\u00A0'],
                     'y': [u'\u00A0--\u00A0', u'\u00A0'],
                     'z': [u'\u00A0--\u00A0', u'\u00A0']
                     }

    typeDict = {'persname': persnamePunct,
                'famname': famnamePunct,
                'corpname': corpnamePunct,
                'subject': subjectPunct,
                'geogname': geognamePunct
                }

    def __init__(self, lgr=None):
        EadHandler.__init__(self, lgr)
        self.htmlTitle = ['Data Creation and Editing']
        self.htmlNav = ['<a href="menu.html" title="Edit/Create Menu">'
                        'Edit/Create Menu</a>',
                        '<a href="/ead/edit/help.html" '
                        'title="Edit/Create Help">Edit/Create Help</a>',
                        '<a href="javascript: toggleKeyboard();" '
                        'title="Show/Hide Character Keyboard">'
                        'Character Keyboard</a>']
        # End __init__ ------------------------------------------------------

    def _shortFieldName(self, field):
        try:
            return field.name[:field.name.rfind('[')]
        except:
            return field.name

    def send_html(self, data, req, code=200):
        req.headers_out['Cache-Control'] = "no-cache, no-store"
        super(EadEditingHandler, self).send_html(data, req, code)
        # End send_html() ---------------------------------------------------

    def send_fullHtml(self, data, req, code=200):
        # Read the template in
        tmpl = read_file(self.templatePath)
        page = tmpl.replace("%CONTENT%", data)
        self.globalReplacements.update({
            "%TITLE%": title_separator.join(self.htmlTitle),
            "%NAVBAR%": navbar_separator.join(self.htmlNav),
        })
        page = multiReplace(page, self.globalReplacements)
        req.content_type = 'text/html'
        req.headers_out['Cache-Control'] = "no-cache, no-store"
        req.content_length = len(page)
        req.send_http_header()
        if (type(page) == unicode):
            page = page.encode('utf-8')
        req.write(page)
        req.flush()        
        # End send_html() ---------------------------------------------------
    
    def send_xml(self, data, req, code=200):
        req.headers_out['Cache-Control'] = "no-cache, no-store"
        super(EadEditingHandler, self).send_xml(data, req, code)
        # End send_xml() ----------------------------------------------------
    
    def _validate_isadg(self, rec):
        required_xpaths = ['/ead/eadheader/eadid']
        # check record for presence of mandatory XPaths
        missing_xpaths = []
        for xp in required_xpaths:
            try:
                rec.process_xpath(session, xp)[0]
            except IndexError:
                missing_xpaths.append(xp)
        if len(missing_xpaths):
            self.htmlTitle.append('Error')
            newlineRe = re.compile('(\s\s+)')
            return '''
    <p class="error">
    Your file does not contain the following mandatory XPath(s):<br/>
    %s
    </p>
    <pre>
    %s
    </pre>
    ''' % ('<br/>'.join(missing_xpaths),
           newlineRe.sub('\n\g<1>',
                         html_encode(rec.get_xml(session))
                         )
           )
        else:
            return None
        # End _validate_isadg() ---------------------------------------------
        
    # Template creation/editing functions====================================

    def create_template(self, form):
        self.log('CREATING NEW TEMPLATE') 
        self.htmlNav = ['<a href="menu.html" title="Edit/Create Menu">'
                        'Edit/Create Menu</a>',
                        '<a href="/ead/edit/help.html" target="_new"  '
                        'title="Edit/Create Help">Edit/Create Help</a>',
                        '<a href="javascript: toggleKeyboard();" '
                        'title="Show/Hide Character Keyboard">'
                        'Character Keyboard</a>']
        structure = read_file('eadtemplate.html')  
        doc = StringDocument('<template><ead><eadheader></eadheader>'
                             '<archdesc></archdesc></ead></template>')      
        rec = xmlp.process_document(session, doc)
        htmlform = formTxr.process_record(session, rec).get_raw(session)
        page = structure.replace('%FRM%', htmlform)
        page = page.replace('%RECID%', '')
        page = page.replace('%PUI%',
                            '<input type="hidden" name="pui" id="pui"/>')
        page = page.replace('%TOC%', '')  
        page = page.replace('%MENUCODE%',
                            read_file('contextMenu.html'))    
        page = page.replace('%KYBDCODE%',
                            read_file('keyboard.html'))
        return page

    def modify_template(self, form):
        self.log('MODIFYING TEMPLATE')
        templateName = form.get('templatesel2', None)
        if templateName is None:
            self.create_template(self, form)
        else:
            self.htmlNav = ['<a href="menu.html" title="Edit/Create Menu">'
                            'Edit/Create Menu</a>',
                            '<a href="/ead/edit/help.html" target="_new" '
                            'title="Edit/Create Help">Edit/Create Help</a>',
                            '<a href="javascript: toggleKeyboard();" '
                            'title="Show/Hide Character Keyboard">'
                            'Character Keyboard</a>'
                            ]
            structure = read_file('eadtemplate.html')
            templateStore = db.get_object(session, 'templateStore')
            rec = templateStore.fetch_record(session, templateName)
            htmlform = formTxr.process_record(session, rec).get_raw(session)
            page = structure.replace('%FRM%', htmlform)
            page = page.replace('%RECID%', '')
            page = page.replace('%PUI%',
                                '<input type="hidden" name="pui" id="pui"/>')
            page = page.replace('%TOC%', '')  
            page = page.replace('%MENUCODE%', read_file('contextMenu.html'))
            page = page.replace('%KYBDCODE%', read_file('keyboard.html'))   
            return page

    def save_template(self, form):
        self.log('SAVING TEMPLATE')
        templateStore = db.get_object(session, 'templateStore')
        templateStore.begin_storing(session)
        #build template xml
        (templateXml, name) = self.build_ead(form, True)        
        doc = StringDocument(etree.tostring(templateXml))
        rec = xmlp.process_document(session, doc)
        
        rec.id = name.strip()
        #otherwise store in template store and create institution link
        templateStore.store_record(session, rec)
        templateStore.commit_storing(session)
        return '<name>%s</name>' % rec.id

    def discard_template(self, form):
        templateStore = db.get_object(session, 'templateStore')
        templateStore.begin_storing(session)
        recid = form.get('recid', None)
        if not recid is None:
            try:
                templateStore.delete_record(session, recid)
                templateStore.commit_storing(session)
                return 'done'   
            except:
                return 'failed'
           
        else:
            return 'failed'    

    # EAD Creation and Editing Functions ====================================

    def build_ead(self, form, template=False):
        self.log('building ead')
        if template:
            name = form.get('/template/@name', None)
            tree = etree.fromstring('<template name="%s">'
                                    '<ead>'
                                    '<eadheader></eadheader>'
                                    '<archdesc></archdesc>'
                                    '</ead>'
                                    '</template>' % name)
            header = tree.xpath('/template/ead/eadheader')[0]
            target = self._create_path(header,
                                       'filedesc/titlestmt/titleproper')
            self._add_text(target, form.get('did/unittitle', ''))     
            if form.get('filedesc/titlestmt/sponsor', '') != '': 
                target = self._create_path(header,
                                           'filedesc/titlestmt/sponsor')   
                self._add_text(target,
                               form.get('filedesc/titlestmt/sponsor', ''))
            mylist = form.list  
            daonames = {}
            node = tree.xpath('/template/ead/archdesc')[0]
            for field in mylist:
                if field.name not in ['ctype',
                                      'location',
                                      'operation',
                                      'newForm',
                                      'owner',
                                      'recid',
                                      'parent',
                                      'pui',
                                      'eadid',
                                      'filedesc/titlestmt/sponsor',
                                      'daoselect',
                                      'tempid']:                        
                    # Do did level stuff
                    if field.name.find('controlaccess') == 0:
                        self._create_controlaccess(node,
                                                   field.name,
                                                   field.value) 
                        try:
                            validList.remove('controlaccess')
                        except:
                            pass
                    elif field.name.find('did/langmaterial') == 0:
                        did = self._create_path(node, 'did')
                        self._create_langmaterial(did, field.value)
                        try:
                            validList.remove('did/langmaterial/language')
                        except:
                            pass
                    elif field.name.find('dao') == 0:
                        daoname = field.name.split('|')
                        daodict = daonames.get(daoname[0], {})
                        val = field.value
                        if (val.strip() != '' and
                            val.strip() != ' ' and 
                            va.strip() != '<p></p>' and 
                            re.sub('[\s]+',
                                   ' ',
                                   val.strip()
                                   ) != '<p> </p>'):
                            
                            daodict[daoname[1]] = val
                        daonames[daoname[0]] = daodict                
                    else:
                        if (field.value.strip() != '' and
                            field.value.strip() != ' ' and
                            field.value.strip() != '<p></p>' and
                            re.sub('[\s]+',
                                   ' ',
                                   field.value.strip()
                                   ) != '<p> </p>'):
                            target = self._create_path(node, field.name)
                            self._add_text(target, field.value)
                            field_name = self._shortFieldName(field)
                            try:
                                validList.remove(field_name)
                            except:
                                pass
            self._create_dao(daonames, node)
            self.log('build complete')
            return (tree, name)

        ctype = form.get('ctype', None)
        loc = form.get('location', None)
        collection = False
        validList = None
        if (loc == 'collectionLevel'):
            validList = [l for l in self.required_xpaths]
            collection = True
            #set all the ead header info
            tree = etree.fromstring('<ead><eadheader></eadheader>'
                                    '<archdesc></archdesc></ead>')           
            header = tree.xpath('/ead/eadheader')[0]
            target = self._create_path(header, 'eadid')
            if form.get('eadid', '') != '':
                self._add_text(target, form.get('eadid', ''))            
            else:
                self._add_text(target, form.get('pui', ''))
            target = self._create_path(header,
                                       'filedesc/titlestmt/titleproper')
            self._add_text(target, form.get('did/unittitle', ''))     
            if form.get('filedesc/titlestmt/sponsor', '') != '': 
                target = self._create_path(header,
                                           'filedesc/titlestmt/sponsor')   
                self._add_text(target,
                               form.get('filedesc/titlestmt/sponsor', '')) 
            target = self._create_path(header, 'profiledesc/creation')
            if session.user.realName != '':
                userName = session.user.realName
            else:
                userName = session.user.username
            self._add_text(target,
                           'Created by {0} using the Cheshire for Archives '
                           'EAD Editor.'.format(userName))
            target = self._create_path(header, 'profiledesc/creation/date')
            today = datetime.date.today()
            target.attrib.update({'normal': today.isoformat()})
            self._add_text(target, today.strftime('%d %B %Y'))
        else:
            validList = [l for l in self.required_xpaths_components]
            tree = etree.fromstring('<%s c3id="%s"></%s>'
                                    '' % (ctype, loc, ctype))   
        # Build the rest of the ead        
        mylist = form.list  
        daonames = {}   
        if (collection):
            node = tree.xpath('/ead/archdesc')[0]
        else:
            node = tree.xpath('/*[not(name() = "ead")]')[0]
        for field in mylist:
            if field.name not in ['ctype',
                                  'location',
                                  'operation',
                                  'newForm',
                                  'owner',
                                  'recid',
                                  'parent',
                                  'pui',
                                  'eadid',
                                  'filedesc/titlestmt/sponsor',
                                  'daoselect']:                        

                # Do did level stuff
                if field.name.find('controlaccess') == 0:
                    self._create_controlaccess(node, field.name, field.value) 
                    try:
                        validList.remove('controlaccess')
                    except:
                        pass
                elif field.name.find('did/langmaterial') == 0:
                    did = self._create_path(node, 'did')
                    self._create_langmaterial(did, field.value)
                    try:
                        validList.remove('did/langmaterial/language')
                    except:
                        pass
                elif field.name.startswith('dao'):
                    daoname = field.name.split('|')
                    daodict = daonames.get(daoname[0], {})
                    val = field.value
                    if (val.strip() != '' and
                        val.strip() != ' ' and
                        val.strip() != '<p></p>' and
                        re.sub('[\s]+',
                               ' ',
                               val.strip()
                               ) != '<p> </p>'):
                        daodict[daoname[1]] = val
                    daonames[daoname[0]] = daodict                
                else:
                    if (field.value.strip() != '' and
                        field.value.strip() != ' ' and
                        field.value.strip() != '<p></p>' and
                        re.sub('[\s]+',
                               ' ',
                               field.value.strip()
                               ) != '<p> </p>'):
                        target = self._create_path(node, field.name)
                        self._add_text(target, field.value)
                        field_name = self._shortFieldName(field)
                        try:
                            validList.remove(field_name)
                        except:
                            pass
        self.log(daonames)   
        self._create_dao(daonames, node)
        if (len(validList)):
            valid = False
        else:
            valid = True
        self.log('build complete')
        return (tree, valid)    
        # End build_ead    
        
    def _create_dao(self, dao_dict, node):
        if node.xpath('did'):
            startnode = node.xpath('did')[0]
        else:
            startnode = self._create_path(node, 'did')
        for k in sorted(dao_dict):
            dao = dao_dict[k]
            keys = dao.keys()
            if 'new' in keys or 'embed' in keys:
                # simple <dao>
                if 'href' in keys:
                    daoelem = etree.Element('dao')
                    daoelem.attrib['href'] = dao['href']
                    try:
                        # embedded image
                        daoelem.attrib['show'] = dao['embed']
                    except KeyError:
                        # link
                        daoelem.attrib['show'] = dao['new']
                    if 'desc' in keys:
                        descelem = etree.Element('daodesc')
                        self._add_text(descelem, dao['desc'])
                        daoelem.append(descelem)
                    startnode.append(daoelem)
            elif 'thumb' in keys:
                # thumbnail daogrp
                if 'href1' in keys and 'href2' in keys:
                    daoelem = etree.Element('daogrp')
                    startnode.append(daoelem)
                    daoloc = etree.Element('daoloc')
                    daoloc.attrib['href'] = dao['href1']
                    daoloc.attrib['role'] = dao['thumb']
                    daoelem.append(daoloc)
                    daoloc = etree.Element('daoloc')
                    daoloc.attrib['href'] = dao['href2']
                    daoloc.attrib['role'] = dao['reference']
                    daoelem.append(daoloc)      
                    if 'desc' in keys:
                        descelem = etree.Element('daodesc')
                        self._add_text(descelem, dao['desc'])
                        daoelem.append(descelem)                     
            else:
                # regular daogrp
                hrefpresent = False
                hrefs = []
                for key in keys:                   
                    if key.startswith('href'):
                        hrefs.append(key)
                self.log(hrefs)
                if len(hrefs) > 0:
                    daoelem = etree.Element('daogrp')
                    startnode.append(daoelem)  
                    for i in range(1, len(hrefs) + 1):
                        daoloc = etree.Element('daoloc')
                        daoloc.attrib['href'] = dao['href%d' % i]
                        daoloc.attrib['role'] = dao['role%d' % i]
                        if 'title%d' % i in keys:
                            daoloc.attrib['title'] = dao['title%d' % i]
                        daoelem.append(daoloc)
                    if 'desc' in keys:
                        descelem = etree.Element('daodesc')
                        self._add_text(descelem, dao['desc'])
                        daoelem.append(descelem)
                      
    def _delete_path(self, startNode, nodePath):
        if not (startNode.xpath(nodePath)):
            return 
        else:
            if nodePath.find('@') > -1:
                string = nodePath[nodePath.rfind('@') + 1:]
                if nodePath.find('/') == -1: 
                    parent = startNode
                else:
                    pxp = ''.join(nodePath[:nodePath.rfind('/')])
                    parent = startNode.xpath(pxp)[0]  
                del parent.attrib[string] 
            else:
                child = startNode.xpath(nodePath)[0]
                if child.tag == 'dao':
                    if child.get('href') is not None:
                        return
                if nodePath.find('/') == -1:
                    parent = startNode
                else:
                    pxp = ''.join(nodePath[:nodePath.rfind('/')])
                    parent = startNode.xpath(pxp)[0]
                parent.remove(child)
            if len(parent.getchildren()) > 0 or parent.text is not None:
                return
            else:
                return self._delete_path(startNode,
                                         nodePath[:nodePath.rfind('/')])

    def _create_path(self, startNode, nodePath):              
        if (startNode.xpath(nodePath)):
            if (nodePath.find('@') == -1):
                return startNode.xpath(nodePath)[0]
            else:  
                if len(startNode.xpath(nodePath[:nodePath.rfind('/')])) > 0:
                    parent = startNode.xpath(nodePath[:nodePath.rfind('/')])[0]
                else:
                    parent = startNode
                attribute = nodePath[nodePath.rfind('@') + 1:]
                return [parent, attribute]
        elif (nodePath.find('@') == 0):
            return self._add_attribute(startNode, nodePath[1:])
        elif (nodePath.find('/') == -1):
            if nodePath.find('[') != -1:
                newNode = etree.Element(nodePath[:nodePath.find('[')])   
            else:
                newNode = etree.Element(nodePath)                     
            return self._append_element(startNode, newNode)
        else:
            newNodePath = ''.join(nodePath[:nodePath.rfind('/')]) 
            nodeString = ''.join(nodePath[nodePath.rfind('/') + 1:])  
            if (nodeString.find('@') != 0):      
                if nodeString.find('[') != -1:
                    newNode = etree.Element(nodeString[:nodeString.find('[')])
                else:
                    newNode = etree.Element(nodeString)
                el = self._create_path(startNode, newNodePath)
                return self._append_element(el, newNode)
            else:
                el = self._create_path(startNode, newNodePath)
                return self._add_attribute(el, nodeString[1:])  
            
    def _append_element(self, parentNode, childNode):    
        parentNode.append(childNode)
        return childNode
    
    def _add_attribute(self, parentNode, attribute):
        parentNode.attrib[attribute] = ""
        return [parentNode, attribute]

    def _delete_currentControlaccess(self, startNode,
                                     mylist=['subject',
                                             'persname',
                                             'famname',
                                             'corpname',
                                             'geogname',
                                             'title',
                                             'genreform',
                                             'function']):
        if (startNode.xpath('controlaccess')):
            parent = startNode.xpath('controlaccess')[0]        
            for s in mylist:
                if (parent.xpath('%s' % s)):
                    child = parent.xpath('%s' % s)
                    for c in child:
                        parent.remove(c)
            if len(parent.getchildren()) == 0:
                startNode.remove(parent)
            
    def _delete_currentLangmaterial(self, startNode):
        did = startNode.xpath('did')[0]
        if (did.xpath('langmaterial')):
            parent = did.xpath('langmaterial')[0]
            child = parent.xpath('language')
            if len(child) > 0:
                for c in child:
                    parent.remove(c)
            did.remove(parent)
    
    def _delete_currentDao(self, startNode):
        #delete dao from outside did
        children = startNode.xpath('dao')
        if len(children) > 0:
            for c in children:
                startNode.remove(c)
        #delete daogrp from outside did
        children = startNode.xpath('daogrp')
        if len(children) > 0:
            for c in children:
                startNode.remove(c)        
        did = startNode.xpath('did')[0]
        #delete dao from inside did
        children = did.xpath('dao')
        if len(children) > 0:
            for c in children:
                did.remove(c)               
        #delete daogrp from inside did
        children = did.xpath('daogrp')
        if len(children) > 0:
            for c in children:
                did.remove(c)   
      
    def _create_langmaterial(self, startNode, value, name=None):
        if not (startNode.xpath('langmaterial')):
            langmaterial = etree.Element('langmaterial')
            startNode.append(langmaterial)
            lmNode = langmaterial
        else:
            lmNode = startNode.xpath('langmaterial')[0]        
        fields = value.split(' ||| ')
        language = etree.SubElement(lmNode,
                                    'language',
                                    langcode='%s' % fields[0].split(' | ')[1])     
        text = fields[1].split(' | ')[1]
        self._add_text(language, text)

    def _add_text(self, parent, textValue):
        if not (textValue.find('&amp;') == -1):
            textValue = textValue.replace('&amp;', '&#38;')
        else: 
            if not (textValue.find('&') == -1):
                regex = re.compile('&(?!#[0-9]+;)')
                textValue = regex.sub('&#38;', textValue)
        textValue = textValue.lstrip()      
        if isinstance(parent, etree._Element):
            for c in parent.getchildren():
                parent.remove(c)
            value = '<foo>%s</foo>' % textValue      
            try:
                nodetree = etree.fromstring(value)               
            except:
                self.errorFields.append(parent.tag)
                parent.text = textValue
            else:
                parent.text = nodetree.text
                for n in nodetree:
                    parent.append(n)
        else:
            parent[0].attrib[parent[1]] = textValue
       
    def _create_controlaccess(self, startNode, name, value):
        #get the controlaccess node or create it 
        if not (startNode.xpath('controlaccess')):
            controlaccess = etree.Element('controlaccess')
            startNode.append(controlaccess)
            caNode = controlaccess
        else:
            caNode = startNode.xpath('controlaccess')[0]   
        typeString = name[name.find('/') + 1:]    
        type = etree.Element(typeString)
        caNode.append(type)
        fields = value.split(' ||| ')
        for i, f in enumerate(fields):
            if not (f == ''):
                field = f.split(' | ')
                typelabel = field[0].split('_')[0]
                fieldlabel = field[0].split('_')[1]
                if (fieldlabel == 'source' or
                        fieldlabel == 'rules' or
                        typelabel == 'att'):
                    if (field[1] != 'none'):
                        type.set(fieldlabel, field[1].lower())                         
                else:
                    try:
                        punctList = self.typeDict[typeString]
                    except:
                        punctList = None                      
                    if (fieldlabel == typelabel):
                        attributeValue = 'a'
                    else:
                        attributeValue = self.altrenderDict.get(fieldlabel,
                                                                None)
                        if attributeValue is None:
                            attributeValue = fieldlabel
                    emph = etree.Element('emph',
                                         altrender='%s' % attributeValue)
                    self._add_text(emph, field[1])
                    if i < len(fields):
                        if punctList and punctList.get(attributeValue, None):
                            punct = punctList.get(attributeValue, None)
                            if len(punct) == 1:
                                emph.tail = punct[0]
                            else:
                                type[-1].tail = '%s%s' % (type[-1].tail,
                                                          punct[0])
                                emph.tail = punct[1]
                        else:
                            emph.tail = u'\u00A0'
                    type.append(emph)    
        lastTail = type[-1].tail   
        if re.match('(\s+)?[,\.\-](\s+)?', lastTail):
            type[-1].tail = ''
         
        #- end _create_controlacess    
 
    # Navigation related functions ==========================================
       
    def navigate(self, form): 
        recid = form.get('recid', None)
        owner = form.get('owner', session.user.username)
        new = form.get('newForm', None)
        page = self.populate_form(recid, owner, new, form)  
        return page    
    
    def populate_form(self, recid, owner, new, form):  
        retRec = editStore.fetch_record(session, '%s-%s' % (recid, owner)) 
        if (new == 'collectionLevel'):
            # If its collection level give the transformer the whole record
            retrievedDom = retRec.get_dom(session)
            rec = LxmlRecord(retrievedDom)
        else:
            # If its a component find the component by id and just give that
            # component to the transformer
            retrievedXml = retRec.get_xml(session)
            root = None
            tree = etree.fromstring(retrievedXml)
            comp = tree.xpath('//*[@c3id=\'%s\']' % new)
            try:
                root = comp[0]
            except:
                pass
                      
            if root is None:
                ctype = form.get('ctype', 'c')
                doc = StringDocument('<%s><recid>%s</recid></%s>'
                                     '' % (ctype, recid, ctype))
                rec = xmlp.process_document(session, doc)
            else:
                rec = LxmlRecord(root) 
        
        page = formTxr.process_record(session, rec).get_raw(session)
        page = page.replace('%PUI%',
                            '<input type="text" onfocus="setCurrent(this);" '
                            'name="pui" id="pui" size="30" disabled="true" '
                            'value="%s"/>' % recid)
        return page.replace('%RECID%', '')

    # Loading in related functions ==========================================
    
    def _add_componentIds(self, rec):
        tree = etree.fromstring(rec.get_xml(session))
        compre = re.compile('^c[0-9]*$')
        for element in tree.iter(tag=etree.Element):
            if compre.match(element.tag): 
                try:                 
                    # Add the appropriate id!
                    posCount = 1
                    parentId = ''
                    for el in element.itersiblings(tag=etree.Element,
                                                   preceding=True):
                        if compre.match(el.tag):
                            posCount += 1
                    # Get the parent component id and use it 
                    for el in element.iterancestors():
                        if compre.match(el.tag):
                            parentId = el.get('c3id')                             
                            break
                    idString = '%s-%d' % (parentId, posCount)
                    if idString[0] == '-':
                        idString = idString[1:]
                    element.set('c3id', idString)                       
                except:
                    raise
        return LxmlRecord(tree)
                    
    def generate_file(self, form):
        self.log('CREATING NEW FILE')
        structure = read_file('ead2002.html')
        templateStore = db.get_object(session, 'templateStore')
        templateName = form.get('templatesel1', None)  
        if templateName is None or templateName == 'blank':
            doc = StringDocument('<ead><eadheader></eadheader>'
                                 '<archdesc></archdesc></ead>')      
            rec = xmlp.process_document(session, doc)
        else:
            try:
                tmplRec = templateStore.fetch_record(session, templateName)
                tree = tmplRec.get_dom(session)
                newtree = tree.xpath('/template/ead')[0]
                rec = xmlp.process_document(session,
                                            StringDocument(
                                                etree.tostring(newtree)
                                            )
                                            )
            except:
                doc = StringDocument('<ead><eadheader></eadheader>'
                                     '<archdesc></archdesc></ead>')      
                rec = xmlp.process_document(session, doc)

        htmlform = formTxr.process_record(session, rec).get_raw(session)
        page = structure.replace('%FRM%', htmlform) 
        page = page.replace('%RECID%',
                            '<input type="hidden" id="recid" value="notSet"/>')
        page = page.replace('%PUI%',
                            '<input type="text" onfocus="setCurrent(this);" '
                            'name="pui" id="pui" size="30" readonly="true" '
                            'class="readonly"/>')
        page = page.replace('%TOC%', '<b><a id="collectionLevel" name="link" '
                            'class="valid" onclick="javascript: '
                            'displayForm(this.id)" style="display:inline; '
                            'background:yellow">Collection Level</a></b>')  
        page = page.replace('%MENUCODE%', read_file('contextMenu.html'))    
        page = page.replace('%KYBDCODE%', read_file('keyboard.html'))
        return page
  
    def _add_revisionDesc(self, rec, fn, local=False):
        tree = rec.get_dom(session)
        filename = fn[fn.rfind('/data/') + 6:]
        if session.user.realName != '':
            userName = session.user.realName
        else:
            userName = session.user.username
        if local:
            textString = ('Uploaded from a local file and edited by {0} using '
                          'the Cheshire for Archives EAD Editor.'
                          ''.format(userName)
                          )  
        else:
            textString = ('Loaded from {0} and edited by {1} using the '
                          'Cheshire for Archives EAD Editor.'
                          ''.format(filename, userName)
                          )
        
        today = datetime.date.today()
        if tree.xpath('/ead/eadheader/revisiondesc'):
            if tree.xpath('/ead/eadheader/revisiondesc/change'):
                parent = tree.xpath('/ead/eadheader/revisiondesc')[0]
                new = etree.Element('change')
                date = etree.Element('date')
                date.set('normal', today.isoformat())
                date.text = today.strftime('%d %B %Y')
                new.append(date)
                item = etree.Element('item')
                item.text = textString
                new.set('audience', 'internal')
                new.append(item)
                parent.append(new)
            elif tree.xpath('/ead/eadheader/revisiondesc/list'):
                parent = tree.xpath('/ead/eadheader/revisiondesc/list')[0]
                item = etree.Element('item')
                item.set('audience', 'internal')
                item.text = '{0} on {1}'.format(textString,
                                                today.strftime('%d %B %Y'))
                parent.append(item)
        else:
            header = tree.xpath('/ead/eadheader')[0]
            target = self._create_path(
                header,
                '/ead/eadheader/revisiondesc/change'
            )
            target.set('audience', 'internal')
            target = self._create_path(
                header,
                '/ead/eadheader/revisiondesc/change/date'
            )
            target.set('normal', today.isoformat())
            self._add_text(target, today.strftime('%d %B %Y'))
            target = self._create_path(
                header,
                '/ead/eadheader/revisiondesc/change/item'
            )          
            self._add_text(target, textString)   
        return LxmlRecord(tree)

    #loads from editStore
    def load_file(self, form, req):        
        recid = form.get('recid', None)
        self.log('LOADING RECORD - %s' % recid)
        found = False
        if not recid:
            return self.show_editMenu()
        try:
            rec = editStore.fetch_record(session, recid)
            found = True
        except:
            try:
                recid = '%s-%s' % (recid, session.user.username)
                rec = editStore.fetch_record(session, recid)
                found = True
            except:
                return self.show_editMenu()
        if found:
            structure = read_file('ead2002.html') 
            htmlform = formTxr.process_record(session, rec).get_raw(session)
            page = structure.replace('%FRM%', htmlform) 
            splitId = recid.split('-')
            page = page.replace('%RECID%',
                                '<input type="hidden" id="recid" value="%s"/>'
                                '' % '-'.join(splitId[:-1]))
            if splitId[-1] == session.user.username:
                page = page.replace('%PUI%',
                                    '<input type="text" '
                                    'onfocus="setCurrent(this);" '
                                    'name="pui" id="pui" size="30" '
                                    'disabled="true" value="%s"/>'
                                    '' % '-'.join(splitId[:-1]))
            else:
                page = page.replace('%PUI%',
                                    '<input type="text" '
                                    'onfocus="setCurrent(this);" '
                                    'name="pui" id="pui" size="30" '
                                    'disabled="disabled" value="%s"/>'
                                    '<input type="hidden" id="owner" '
                                    'value="%s"/>'
                                    '' % ('-'.join(splitId[:-1]), splitId[-1]))                             
            page = page.replace('%TOC%',
                                tocTxr.process_record(session,
                                                      rec).get_raw(session))
            page = page.replace('%MENUCODE%', read_file('contextMenu.html'))
            page = page.replace('%KYBDCODE%', read_file('keyboard.html'))
            return page
        
    # Loads from file
    
    def edit_file(self, form):
        f = form.get('filepath', None)
        self.log('LOADING FROM FILE %s' % f)
        if not f or not len(f.value):
            return self.show_editMenu()
        ws = re.compile('[\s]+')
        xml = ws.sub(' ', read_file(f))
        rec = self._add_componentIds(self._parse_upload(xml))       
        # TODO: handle file not successfully parsed
        if not isinstance(rec, LxmlRecord):
            return rec 
        if rec.process_xpath(session, '/ead/eadheader'):
            # Add necessary information to record and get id'
            rec1 = self._add_revisionDesc(rec, f)
            rec2 = assignDataIdFlow.process(session, rec1)
            recid = rec2.id       
            id = '%s-%s' % (recid,
                            session.user.username.encode('ascii', 'ignore'))
            rec2.id = id
            self.log('record has id %s' % recid)
            # If the file exists in the record store load from there
            # (fixes problems with back button)
            try:
                rec2 = editStore.fetch_record(session, id)
            except:
                # Otherwise store in editing store
                editStore.store_record(session, rec2)
#            editStore.commit_storing(session) 
            structure = read_file('ead2002.html')
            htmlform = formTxr.process_record(session, rec2).get_raw(session)
            page = structure.replace('%FRM%', htmlform)
            page = page.replace('%RECID%',
                                '<input type="hidden" id="recid" value="%s"/>'
                                '' % (recid.encode('ascii')))
            page = page.replace('%PUI%',
                                '<input type="text" '
                                'onfocus="setCurrent(this);" name="pui" '
                                'id="pui" size="30" disabled="disabled" '
                                'value="%s"/><input type="hidden" '
                                'id="filename" value="%s"/>'
                                '' % (recid.encode('ascii'), f)
                                )
            page = page.replace('%TOC%',
                                tocTxr.process_record(session,
                                                      rec2).get_raw(session))
            page = page.replace('%MENUCODE%', read_file('contextMenu.html'))
            page = page.replace('%KYBDCODE%', read_file('keyboard.html'))
            return page    
        else:
            return ('<p>Your file is not compatible with the editing interface'
                    ' - it requires an eadheader element</p>')
         
    def upload_local(self, form):
        f = form.get('filepath', None)
        self.log('LOADING FROM FILE local file store')
        if not f or not len(f.value):
            return self.show_editMenu()
        ws = re.compile('[\s]+')
        xml = ws.sub(' ', f.value)
        rec = self._parse_upload(xml, 'edit')
          
        # TODO: handle file not successfully parsed
        if not isinstance(rec, LxmlRecord):
            return rec
        rec = self._add_componentIds(rec)     
        if rec.process_xpath(session, '/ead/eadheader'):
            #add necessary information to record and get id'
            rec = self._add_revisionDesc(rec, '', True)
            rec1 = assignDataIdFlow.process(session, rec)
            recid = rec1.id   
            
            idCheck = self.checkExistingId(rec1.id)
            if idCheck[0]:
                if idCheck[1] == 'recordStore':
                    self.log('Already in database')
                    return ('<p>The file you have requested cannot be uploaded'
                            ' because a file with the same ID already exists '
                            'in your spoke database.'
                            '<br/><br/>'
                            'In order to edit this file you must import it '
                            'from the spoke database rather than uploading '
                            'from your local file store.</p><br/>'
                            '<a href="/ead/edit/editmenu.html">'
                            'Back to Create/Edit Menu</a>')
                else:
                    if idCheck[2]:
                        self.log('Already in draft file store')
                        return ('<p>You already have this file open for '
                                'editing as %s. <br/><br/>'
                                'To continue editing the version of the file '
                                'in the Draft File Store click '
                                '<a href="/ead/edit/?operation=load&'
                                'user=null&recid=%s-%s">here</a>. '
                                '(if you reached this page by using the back '
                                'button from a preview of the record then '
                                'this will take you back to the record you '
                                'were editing)<br/><br/>'
                                'To edit the version from your local file '
                                'store please delete the file currently in '
                                'the Draft File Store before reloading</p>'
                                '<br/><a href="/ead/edit/editmenu.html">'
                                'Back to Create/Edit Menu</a>'
                                '' % (rec1.id,
                                      rec1.id,
                                      session.user.username.encode('ascii',
                                                                   'ignore')
                                      )
                                )
                    else:
                        pass
            id = '%s-%s' % (recid,
                            session.user.username.encode('ascii', 'ignore'))
            rec1.id = id
            self.log('record has id %s' % recid)
            # If the file exists in the record store load from there
            # (fixes problems with back button)
            try:
                rec1 = editStore.fetch_record(session, id)
            except:
            # Otherwise store in editing store
                editStore.store_record(session, rec1)
#            editStore.commit_storing(session) 
            structure = read_file('ead2002.html')
            htmlform = formTxr.process_record(session, rec1).get_raw(session)
            page = structure.replace('%FRM%', htmlform)
            page = page.replace('%RECID%', '<input type="hidden" id="recid" '
                                'value="%s"/>' % (recid.encode('ascii')))
            page = page.replace('%PUI%', '<input type="text" '
                                'onfocus="setCurrent(this);" name="pui" '
                                'id="pui" size="30" disabled="true" '
                                'value="%s"/>' % (recid.encode('ascii')))
            page = page.replace('%TOC%',
                                tocTxr.process_record(session,
                                                      rec1).get_raw(session))
            page = page.replace('%MENUCODE%', read_file('contextMenu.html'))
            page = page.replace('%KYBDCODE%', read_file('keyboard.html'))
            return page
        else:
            return ('<p>Your file is not compatible with the editing interface'
                    ' - it requires an eadheader element</p>')
    
    # Validation related functions   ======================================== 
    
    def checkExistingId(self, id):
        exists = False
        store = None
        users = []
        overwrite = False
        try:
            recordStore.fetch_record(session, id)
        except (FileDoesNotExistException, ObjectDoesNotExistException):
            pass
        else:
            exists = True
            store = 'recordStore'
        
        if not exists:
            names = []
            for r in editStore:
                if r.id[:r.id.rfind('-')] == id:
                    names.append(r.id[r.id.rfind('-') + 1:])
            if len(names) > 0:
                exists = True
                store = 'editStore'
                for n in names:
                    if n == session.user.username:
                        overwrite = True
                    else:    
                        users.append(n)    
        return [exists, store, overwrite, users]
    
    def getAndCheckId(self, form):
        f = form.get('filepath', None)
        if not f or not len(f.value):
            return '<value>false</value>'
        ws = re.compile('[\s]+')
        try:
            xml = ws.sub(' ', read_file(f))
        except:
            xml = ws.sub(' ', f.value)
        rec = self._parse_upload(xml)
                
        if not isinstance(rec, LxmlRecord):
            return '<value>false</value>'
        
        rec = assignDataIdFlow.process(session, rec)
        names = []
        for r in editStore:
            if r.id[:r.id.rfind('-')] == rec.id:
                names.append(r.id[r.id.rfind('-') + 1:])
        if len(names) == 0:
            return '<value>false</value>'
        else:
            ns = []
            for n in names:
                if n != session.user.username:
                    ns.append(n)
            if len(names) == 1 and names[0] == session.user.username:
                return ('<wrap><value>true</value><overwrite>true</overwrite>'
                        '<id>%s</id></wrap>' % rec.id)
            elif len(names) > 1 and session.user.username in names:
                return ('<wrap><value>true</value><overwrite>true</overwrite>'
                        '<users>%s</users><id>%s</id></wrap>'
                        '' % (' \n '.join(ns), rec.id))
            else:
                return ('<wrap><value>true</value><overwrite>false</overwrite>'
                        '<users>%s</users></wrap>' % ' \n '.join(ns))

    def checkId(self, form):
        id = form.get('id', None)        
        store = form.get('store', None)
        
        if store == 'recordStore':
            rs = recordStore
        elif store == 'editStore':
            rs = editStore
            id = '%s-%s' % (id, session.user.username)
        if (id is not None and store is not None):
            exists = 'false'
            for r in rs:
                if r.id == id:
                    exists = 'true'
                    break
            return '<value>%s</value>' % exists

    def checkEditId(self, form):
        id = form.get('id', None)
        rs = editStore
        fullid = '%s-%s' % (id, session.user.username)
        
        if (id is not None):
            exists = 'false'
            for r in rs:
                if r.id == fullid:
                    exists = 'true'
                    break              
            if exists == 'false':                                  
                for r in rs:
                    if r.id[:r.id.rfind('-')] == id:
                        exists = 'true'
                        break
                return ('<wrapper><value>%s</value>'
                        '<owner>other</owner></wrapper>' % exists)
            else:
                return ('<wrapper><value>%s</value>'
                        '<owner>user</owner></wrapper>' % exists)

    def validate_record(self, xml):
        try:
            etree.fromstring(xml)
            return True
        except:
            return False

    def validateField(self, form):
        self.log('validating field via AJAX')
        text = form.get('text', None)
        if not (text.find('&amp;') == -1):
            text = text.replace('&amp;', '&#38;')
        else: 
            if not (text.find('&') == -1):
                regex = re.compile('&(?!#[0-9]+;)')
                text = regex.sub('&#38;', text)     
        if not text.find('<') == -1:
            try:
                test = etree.fromstring('<foo>%s</foo>' % text)
                return '<value>true</value>'
            except:
                return '<value>false</value>'
        else:
            return '<value>true</value>'

    # Basic User functions - submit preview etc. ============================

    def save_form(self, form):
        loc = form.get('location', None)
        recid = form.get('recid', None)
        parent = form.get('parent', None)
        fileOwner = form.get('owner', session.user.username)
        valid = True
        self.log('Saving Form %s' % recid)
        #if there this is a new collection level file
        if (loc == 'collectionLevel' and (recid is None or recid == 'None')):
            self.log('new collection level')
            #save the form in any free slot
            (temp, valid) = self.build_ead(form)
            rec = LxmlRecord(temp)
            rec = assignDataIdFlow.process(session, rec)
            recid = rec.id
            rec.id = '%s-%s' % (rec.id, fileOwner)
            editStore.store_record(session, rec)
#            editStore.commit_storing(session) 
            return (recid, valid)
        #this is an existing collection level file
        elif (loc == 'collectionLevel'):
            self.log('existing collection level')
            validList = [l for l in self.required_xpaths]
            mylist = form.list  
            #pull existing xml and make into a tree
            retrievedRec = editStore.fetch_record(session,
                                                  '%s-%s' % (recid, fileOwner))
            retrievedXml = retrievedRec.get_xml(session)
            tree = etree.fromstring(retrievedXml)
            node = tree.xpath('/ead/archdesc')[0]         
            #first delete current accesspoints, languages and digital objects
            self._delete_currentControlaccess(node)
            self._delete_currentLangmaterial(node)
            self._delete_currentDao(node)
            #change title in header             
            header = tree.xpath('/ead/eadheader')[0]
            target = self._create_path(header,
                                       'filedesc/titlestmt/titleproper')
            self._add_text(target, form.get('did/unittitle', ''))
            
            # Add/delete sponsor
            spons = form.get('filedesc/titlestmt/sponsor', '')
            if (spons.value.strip() != '' and spons.value.strip() != ' '): 
                target = self._create_path(header,
                                           'filedesc/titlestmt/sponsor')
                self._add_text(target, spons)
            else:
                self._delete_path(header, 'filedesc/titlestmt/sponsor')
                                      
            # Cycle through the form and replace any node that need it
            deleteList = []
            daonames = {} 
            for field in mylist:                
                if field.name not in ['ctype',
                                      'location',
                                      'operation',
                                      'newForm',
                                      'owner',
                                      'recid',
                                      'parent',
                                      'pui',
                                      'filedesc/titlestmt/sponsor',
                                      'daoselect']:               
                    #do archdesc stuff
                    if field.name.find('controlaccess') == 0:                        
                        self._create_controlaccess(node,
                                                   field.name,
                                                   field.value)  
                        try:
                            validList.remove('controlaccess')
                        except:
                            pass
                    elif field.name.find('did/langmaterial') == 0:     
                        if field.name.find('did/langmaterial/@') == 0:
                            target = self._create_path(node, field.name)
                            self._add_text(target, field.value)
                        else:
                            did = self._create_path(node, 'did')
                            self._create_langmaterial(did, field.value)
                        try:
                            validList.remove('did/langmaterial/language')
                        except:
                            pass
                    elif field.name.find('dao') == 0:
                        daoname = field.name.split('|')
                        try:
                            daodict = daonames[daoname[0]]
                        except:
                            daodict = {}
                        if (field.value.strip() != '' and
                            field.value.strip() != ' 'and
                            field.value.strip() != '<p></p>' and
                            re.sub('[\s]+',
                                   ' ',
                                   field.value.strip()) != '<p> </p>'):
                            daodict[daoname[1]] = field.value
                        daonames[daoname[0]] = daodict                           
                    else:
                        if (field.value.strip() != '' and
                            field.value.strip() != ' ' and
                            field.value.strip() != '<p></p>' and
                            re.sub('[\s]+',
                                   ' ',
                                   field.value.strip()) != '<p> </p>'):
                            target = self._create_path(node, field.name)
                            self._add_text(target, field.value)
                            field_name = self._shortFieldName(field)
                            try:
                                validList.remove(field_name)
                            except:
                                pass
                        else:
                            deleteList.append(field.name)      
            if len(deleteList):
                deleteList.sort(reverse=True)
                for name in deleteList:
                    self._delete_path(node, name) 
            self.log(daonames)
            self._create_dao(daonames, node)
              
            if len(validList):
                valid = False
            else:
                valid = True      
            rec = LxmlRecord(tree)
            rec.id = retrievedRec.id
            editStore.store_record(session, rec)
#            editStore.commit_storing(session)
            self.log(rec.get_xml(session))
            return (recid, valid)       
        else:
            # Check if C exists, if not add it, if so replace it
            self.log('component')
            # Pull record from store            
            retrievedRec = editStore.fetch_record(session,
                                                  '%s-%s' % (recid, fileOwner))
            retrievedXml = retrievedRec.get_xml(session)   
            tree = etree.fromstring(retrievedXml)
            # First check there is a dsc element and if not add one
            # (needed for next set of xpath tests)
            if not (tree.xpath('/ead/archdesc/dsc')):
                archdesc = tree.xpath('/ead/archdesc')[0]    
                dsc = etree.Element('dsc')     
                archdesc.append(dsc)    
            if not (tree.xpath('//*[@c3id=\'%s\']' % loc)):
                # If the component does not exist add it
                self.log('new component')
                self.log('parent is %s' % parent)
                if parent == 'collectionLevel':
                    parentNode = tree.xpath('/ead/archdesc/dsc')[0]
                else:
                    parentNode = tree.xpath('//*[@c3id=\'%s\']' % parent)[0]
                (rec, valid) = self.build_ead(form)
                parentNode.append(rec)
                rec = LxmlRecord(tree)
                rec.id = retrievedRec.id
                editStore.store_record(session, rec)
#                editStore.commit_storing(session)   
            else:
                # If the component does exist change it   
                self.log('existing component')
                validList = [l for l in self.required_xpaths_components]
                mylist = form.list
                node = tree.xpath('//*[@c3id=\'%s\']' % loc)[0]
                # First delete current accesspoints, lang material and dao
                self._delete_currentControlaccess(node)
                self._delete_currentLangmaterial(node)
                self._delete_currentDao(node)
                deleteList = []
                daonames = {} 
                for field in mylist:
                    if field.name not in ['ctype',
                                          'location',
                                          'operation',
                                          'newForm',
                                          'owner',
                                          'recid',
                                          'parent', 'daoselect']:  
                        if field.name.find('controlaccess') == 0:                        
                            self._create_controlaccess(node,
                                                       field.name,
                                                       field.value) 
                            try:
                                validList.remove('controlaccess')
                            except:
                                pass     
                        elif field.name.find('did/langmaterial') == 0:
                            if field.name.find('did/langmaterial/@') == 0:
                                target = self._create_path(node, field.name)
                                self._add_text(target, field.value)                        
                            else:
                                did = self._create_path(node, 'did')
                                self._create_langmaterial(did, field.value)
                            try:
                                validList.remove('did/langmaterial/language')
                            except:
                                pass
                            
                        elif field.name.find('dao') == 0:
                            daoname = field.name.split('|')
                            try:
                                daodict = daonames[daoname[0]]
                            except:
                                daodict = {}
                            if (field.value.strip() != '' and
                                field.value.strip() != ' ' and
                                field.value.strip() != '<p></p>' and
                                re.sub('[\s]+',
                                       ' ',
                                       field.value.strip()) != '<p> </p>'):
                                daodict[daoname[1]] = field.value
                            daonames[daoname[0]] = daodict   
                        else:
                            if (field.value.strip() != '' and
                                field.value.strip() != ' ' and
                                field.value.strip() != '<p></p>' and
                                re.sub('[\s]+',
                                       ' ',
                                       field.value.strip()) != '<p> </p>'):
                                target = self._create_path(node, field.name)
                                self._add_text(target, field.value)
                                field_name = self._shortFieldName(field)
                                try:
                                    validList.remove(field_name)
                                except:
                                    pass
                            else:
                                deleteList.append(field.name)
                if len(deleteList):
                    deleteList.sort(reverse=True)
                    for name in deleteList:
                        self._delete_path(node, name) 
                self.log(daonames)    
                self._create_dao(daonames, node)  
                            
                if len(validList):
                    valid = False
                else:
                    valid = True        
                rec = LxmlRecord(tree)
                rec.id = retrievedRec.id
                editStore.store_record(session, rec)
#                editStore.commit_storing(session)
            self.log('saving complete')
            return (recid, valid)
  
    def delete_record(self, form):
        recid = form.get('recid', None)
        if not recid is None:
            editStore.delete_record(session, recid)
        return 'done'  

    def discard_record(self, form):
        recid = form.get('recid', None)
        owner = form.get('owner', session.user.username)
        if not recid is None:
            editStore.delete_record(session, '%s-%s' % (recid, owner))
        return 'done'          

    def preview_file(self, req):
        global session, xmlp
        global repository_name, repository_link, repository_logo
        global cache_path, cache_url, toc_cache_path, toc_cache_url
        global toc_scripts, script, fullTxr, fullSplitTxr
        form = FieldStorage(req)
        self.htmlTitle.append('Preview File')
        try:
            files = glob.glob('%s/preview/%s.*'
                              '' % (toc_cache_path, session.user.username))
            for f in files:
                os.remove(f)
        except:
            pass
        try:          
            files = glob.glob('%s/preview/%s*'
                              '' % (cache_path, session.user.username))
            for f in files:
                os.remove(f)
        except:
            pass
        pagenum = int(form.getfirst('pagenum', 1))
        
        self.log('Preview requested')

        recid = form.get('recid', None)
        fileOwner = form.get('owner', session.user.username)
        if recid is not None and recid != 'null':
            rec = editStore.fetch_record(session,
                                         '%s-%s' % (recid, fileOwner))
            doc = db.get_object(session,
                                'orderingTxr').process_record(session, rec)
            rec = xmlp.process_document(session, doc)
        if not isinstance(rec, LxmlRecord):
            return rec      
        # Ensure restricted access directory exists
        try:
            os.makedirs(os.path.join(cache_path, 'preview'))
            os.makedirs(os.path.join(toc_cache_path, 'preview'))
        except OSError:
            # Already exists
            pass
        # Assign rec.id so that html is stored in a restricted access directory
        recid = rec.id = 'preview/%s' % (session.user.username)
        paramDict = self.globalReplacements
        paramDict.update({'%TITLE%': title_separator.join(self.htmlTitle),
                          '%NAVBAR%': '',
                          'LINKTOPARENT': '',
                          'TOC_CACHE_URL': toc_cache_url,
                          'RECID': recid
                          }
                         )
        try:
            page = self.display_full(rec,
                                     paramDict,
                                     pageNavType="links")[pagenum - 1]
        except IndexError:
            return 'No page number %d' % pagenum
        if not (os.path.exists('%s/%s.inc' % (toc_cache_path, recid))):
            page = page.replace('<!--#include virtual="%s/%s.inc"-->'
                                '' % (toc_cache_url, recid),
                                'There is no Table of Contents for this file.')
        else:
            # Cannot use Server-Side Includes in script generated pages
            # Insert ToC manually
            try:
                page = page.replace('<!--#include virtual="%s/%s.inc"-->'
                                    '' % (toc_cache_url, recid),
                                    read_file('%s/%s.inc'
                                              '' % (toc_cache_path, recid))
                                    )
            except:
                page = page.replace('<!--#include virtual="%s/%s.inc"-->'
                                    '' % (toc_cache_url, recid),
                                    '<span class="error">There was a problem '
                                    'whilst generating the Table of '
                                    'Contents</span>')
        return page
    
    # End preview_file() ----------------------------------------------------

    def preview_xml(self, req, form):
        self.log('XML requested')
        recid = form.get('recid', None)
        fileOwner = form.get('owner', session.user.username)
        if recid is not None and recid != 'null':
            retrievedRec = editStore.fetch_record(session,
                                                  '%s-%s' % (recid, fileOwner))
            txr = db.get_object(session, 'orderingTxr')
            return txr.process_record(session, retrievedRec).get_raw(session)
        else:
            return '<p>Unable to display xml</p>'
    
    def submit(self, req, form):
        global sourceDir, xmlp, lockfilepath
        self.log('File submitted')
        i = form.get('index', 'true')
        if i == 'false':
            index = False
        else:
            index = True
        #test to see if another processes in indexing
        req.content_type = 'text/html'
        req.send_http_header()
        head = self._get_genericHtml('header.html')
        req.write(head)
        if index and os.path.exists(lockfilepath):
            req.write('<div id="single">')
            req.write('<p><span class="error">[ERROR]</span> - '
                      'Another user is already indexing this database. '
                      'Please try again in 10 minutes.</p>\n'
                      '<p><a href="/ead/edit/menu.html">Back to '
                      '\'Editing Menu\'.</a></p>')
            req.write('</div>')
        else:  
            req.write('<div id="single">')
            req.write('Initializing... ')
            ppFlow = db.get_object(session, 'preParserWorkflow')
            indexNewRecordFlow = db.get_object(session,
                                               'indexNewRecordWorkflow')
            compRecordFlow = db.get_object(session, 'buildComponentWorkflow')
            compStore = db.get_object(session, 'componentStore')
            dcRecordStore = db.get_object(session, 'eadDcStore')
            queryFactory = db.get_object(session, 'defaultQueryFactory')
            req.write('<span class="ok">[OK]</span><br/>\n')
            
            recid = form.get('recid', None)
            fileOwner = form.get('owner', session.user.username)
            editRecid = '%s-%s' % (recid.value, fileOwner)
            
            rec = editStore.fetch_record(session, editRecid)
            try:
                filename = form.get('filename', self._get_filename(rec))
            except:
                filename = None
                
            if filename is None:
                filename = '%s.xml' % recid
            
            xml = rec.get_xml(session)    
            valid = self.validate_record(xml)     
            if index:      
                lock = open(lockfilepath, 'w')
                lock.close() 
                try:
                    exists = True 
                    if valid:
                        if index:
                            self.log('Preparing to index file')
                            # Delete and unindex the old version from the
                            # record store
                            try: 
                                oldRec = recordStore.fetch_record(session,
                                                                  recid)
                            except:
                                self.log('New record - nothing to unindex')
                                # This is a new record so we don't need to
                                # delete anything
                                exists = False
                                req.write('looking for record... '
                                          '<span class="ok">[OK]</span> - '
                                          'New Record <br/>\n')
                            else:
                                self.log('Unindexing existing record')
                                req.write('undindexing existing version of '
                                          'record... ')
                                db.unindex_record(session, oldRec)
                                req.write('record unindexed')
                                db.remove_record(session, oldRec)
                                req.write('<span class="ok">[OK]</span><br/>\n'
                                          'Deleting record from stores...')
                                self.log('file unindexed')
                                recordStore.begin_storing(session)
                                recordStore.delete_record(session, oldRec.id)
                                recordStore.commit_storing(session)
                                self.log('deleted from record store')
                                dcRecordStore.begin_storing(session)
                                try:
                                    dcRecordStore.delete_record(session,
                                                                rec.id)
                                except:
                                    pass
                                else:
                                    dcRecordStore.commit_storing(session)
                                self.log('deleted from dc store')                
                                req.write('<span class="ok">[OK]</span><br/>'
                                          '\n')
                                if (len(rec.process_xpath(session, 'dsc')) and
                                        exists):
                                    self.log('unindexing and deleting '
                                             'components')
                                    # Now the tricky bit - component records
                                    compStore.begin_storing(session)
                                    qString = ('ead.parentid exact "%s/%s"'
                                               '' % (oldRec.recordStore,
                                                     oldRec.id))
                                    q = queryFactory.get_query(session,
                                                               qString)
                                    req.write('Removing components...')
                                    rs = db.search(session, q)
                                    for r in rs:
                                        try:
                                            compRec = r.fetch_record(session)
                                        except (FileDoesNotExistException,
                                                ObjectDoesNotExistException):
                                            pass
                                        else:
                                            db.unindex_record(session, compRec)
                                            db.remove_record(session, compRec)
                                            compStore.delete_record(session,
                                                                    compRec.id)
                                    compStore.commit_storing(session)
                                    req.write('<span class="ok">[OK]</span>'
                                              '<br/>\n')
                            # Add and index new record
                            self.log('indexing new record')
                            req.write('indexing new record... ')
                            doc = ppFlow.process(session, StringDocument(xml))
                            rec = xmlp.process_document(session, doc)
                            assignDataIdFlow.process(session, rec)
                            db.begin_indexing(session)
                            recordStore.begin_storing(session)
                            dcRecordStore.begin_storing(session)
                            indexNewRecordFlow.process(session, rec)
                            recordStore.commit_storing(session)
                            dcRecordStore.commit_storing(session)
                            if len(rec.process_xpath(session, 'dsc')):
                                compStore.begin_storing(session)
                                # extract and index components
                                compRecordFlow.process(session, rec)
                                compStore.commit_storing(session)
                                db.commit_indexing(session)
                                db.commit_metadata(session)
                                req.write('<span class="ok">[OK]</span><br/>'
                                          '\n')
                            else:
                                db.commit_indexing(session)
                                db.commit_metadata(session)   
                                req.write('<span class="ok">[OK]</span><br/>'
                                          '\n')                  
                finally:
                    if os.path.exists(lockfilepath):
                        os.remove(lockfilepath)
            self.log('writing to file system')
            req.write('writing to file system... ')
            filepath = os.path.join(sourceDir, filename)
            pre = '<?xml version="1.0" encoding="UTF-8"?>'
            if os.path.exists(filepath):
                os.remove(filepath)
            try:
                fh = open(filepath, 'w')
            except:
                fh = open(os.path.join(sourceDir, '%s.xml' % recid), 'w')
            
            orderTxr = db.get_object(session, 'orderingTxr')
            tempDoc = orderTxr.process_record(session, rec)
            tempRec = xmlp.process_document(session, tempDoc)
            del orderTxr
            indentTxr = db.get_object(session, 'indentingTxr')
            tempDoc = indentTxr.process_record(session, tempRec)
            fh.write('%s\n%s' % (pre, tempDoc.get_raw(session)))
            fh.flush()
            fh.close()    
            editStore.delete_record(session, editRecid)
            editStore.commit_storing(session)
            req.write('<span class="ok">[OK]</span><br/>\n<p>'
                      '<a href="/ead/edit/menu.html">Back to '
                      '\'Editing Menu\'.</a></p>')
            foot = self._get_genericHtml('footer.html')  
            req.write('</div>')        
            req.write(foot)
            self.log('file saved as %s' % filepath)
            return None 
      
    def _get_filename(self, rec):
        tree = rec.get_dom(session)
        if tree.xpath('/ead/eadheader/revisiondesc'):
            if tree.xpath('/ead/eadheader/revisiondesc/change'):
                items = tree.xpath('/ead/eadheader/revisiondesc/change/item')
            elif tree.xpath('/ead/eadheader/revisiondesc/list'):
                items = tree.xpath('/ead/eadheader/revisiondesc/list/item')
            fnre = re.compile('Loaded from ([\S]+) and edited')
            m = re.match(fnre, items[-1].text)
            filename = m.group(1)
            return filename
        else:
            return None
      
    def add_form(self, form):
        recid = form.get('recid', None)
        level = int(form.get('clevel', None))
        stringLevel = '%02d' % (level)
        doc = StringDocument('<c%s><recid>%s</recid></c%s>'
                             '' % (stringLevel, recid, stringLevel))
        rec = xmlp.process_document(session, doc)
        htmlform = formTxr.process_record(session, rec).get_raw(session)
        htmlform = htmlform.replace('%PUI%',
                                    '<input type="text" '
                                    'onfocus="setCurrent(this);" name="pui" '
                                    'id="pui" size="30" disabled="true" '
                                    'value="%s"/>' % recid
                                    )
        return htmlform

    def delete_component(self, form):
        recid = form.get('recid', None)
        fileOwner = form.get('owner', session.user.username)
        id = form.get('id', None)   
        retrievedRec = editStore.fetch_record(session,
                                              '%s-%s' % (recid, fileOwner))
        retrievedXml = retrievedRec.get_xml(session)
        tree = etree.fromstring(retrievedXml)      
        comp = tree.xpath('//*[@c3id=\'%s\']' % id)
        if (len(comp) == 1):
            if (id.rfind('-') == -1):
                parent = tree.xpath('//dsc')
            else:                    
                parent = tree.xpath('//*[@c3id=\'%s\']' % id[:id.rfind('-')])
            if len(parent) == 1:
                parent[0].remove(comp[0])
                dsc = tree.xpath('//dsc')[0]
                if len(dsc) == 0:
                    dsc.getparent().remove(dsc)
                rec = LxmlRecord(tree)
                rec.id = retrievedRec.id
                editStore.store_record(session, rec)
                value = 'true'
            else:
                value = 'false'
        else:
            value = 'notsaved'
        return '<value>%s</value>' % value

    def reset(self, form):
        doc = StringDocument('<ead><eadheader></eadheader>'
                             '<archdesc></archdesc></ead>')         
        rec = xmlp.process_document(session, doc)
        page = formTxr.process_record(session, rec).get_raw(session)
        page = page.replace('%RECID%',
                            '<input type="hidden" id="recid" value="notSet"/>')
        page = page.replace('%PUI%',
                            '<input type="text" onfocus="setCurrent(this);" '
                            'name="pui" id="pui" size="30" readonly="readonly"'
                            ' class="readonly"/>')
        return page

    # Menu page functions ===================================================   
    
    def reassign_record(self, form):
        newUser = form.get('user', None).value
        recid = form.get('recid', None).value
        rec = editStore.fetch_record(session, recid)
        if rec.id[rec.id.rfind('-') + 1:] == newUser:
            return recid
        else:
            rec.id = ('%s-%s') % (rec.id[:rec.id.rfind('-')], newUser)
            editStore.delete_record(session, recid)
            id = editStore.store_record(session, rec)           
            #editStore.commit_storing(session)
            return rec.id

    def show_editMenu(self):
        global sourceDir
        page = read_file('editmenu.html')
        #get template info
        templateStore = db.get_object(session, 'templateStore')
        options = []
        for t in templateStore:
            options.append('<option value="%s">%s</option>' % (t.id, t.id))
            
        if len(options) == 0:
            templateSel = ''
            templateMod = ''
        else:
            templateSel = ('<select name="templatesel1">'
                           '<option value="blank">No Template</option>%s'
                           '</select><br/><br/>' % ''.join(options)
                           )
            templateMod = ['<form name="templateform" action="edit.html" '
                           'method="get">',
                           '<input type="hidden" name="operation" '
                           'value="modifytemplate"/>',
                           '<p>Use this to modify an existing template used '
                           'by your institution when creating EAD.</p>', 
                           '<select name="templatesel2">%s</select>'
                           '<br/><br/>'
                           '<input type="submit" value="Modify Template" '
                           'disabled="disabled"/>' % ''.join(options),
                           '</form>'
                           ]
        userStore = db.get_object(session, 'eadAuthStore')
        files = self._walk_directory(sourceDir, 'radio', False)
        recids = self._walk_store(editStore, 'radio', 'eadAuthStore')  
        if session.user.has_flag(session,
                                 'info:srw/operation/1/create',
                                 'eadAuthStore'):
            users = []
            for user in userStore:
                users.append('<option value="%s">%s</option>'
                             '' % (user.username, user.username))
            assignmentOptn = ('<select id="userSelect" name="user" '
                              'disabled="disabled"><option value="null">'
                              'Reassign to...</option>%s</select>'
                              '<input type="button" onclick="reassignToUser()"'
                              ' value="Confirm Reassignment" '
                              'disabled="disabled"/>' % ''.join(users)
                              )
        else:
            assignmentOptn = ''
        return multiReplace(page,
                            {'%%%SOURCEDIR%%%': sourceDir,
                             '%%%FILES%%%': ''.join(files),
                             '%%%RECORDS%%%': ''.join(recids),
                             '%%%USROPTNS%%%': assignmentOptn,
                             '%%%TMPLTSEL%%%': templateSel,
                             '%%%TMPLTMOD%%%': ''.join(templateMod)
                             }
                            ) 
       
    def _walk_store(self, store, type='checkbox', userStore=None):
        if not userStore:
            out = []
            for s in store:
                out.extend(['<li>',
                            '<span class="fileops">'
                            '<input type="%s" name="recid" value="%s"/>'
                            '</span>' % (type, s.id),
                            '<span class="filename">%s</span>' % s.id,
                            '</li>'
                            ]
                           )
            return out
        else:
            out = []
            names = []
            userStore = db.get_object(session, userStore)
            total = 0
            for user in userStore:
                name = user.username
                names.append(name)
                if (name == session.user.username or
                    session.user.has_flag(session,
                                          'info:srw/operation/1/create',
                                          'eadAuthStore')):
                    disabled = ''
                else:
                    disabled = 'disabled="disabled"'
                userFiles = ['<li title=%s><span>%s</span>' % (name, name),
                             '<ul class="hierarchy">'] 
                for s in store:
                    if s.id[s.id.rfind('-') + 1:] == name:
                        try:
                            displayId = s.id[:s.id.rindex('-')]
                        except:
                            displayId = s.id
                        userFiles.extend(['<li>',
                                          '<span class="fileops">'
                                          '<input type="%s" name="recid" '
                                          'value="%s" %s/></span>'
                                          '' % (type, s.id, disabled),
                                          '<span class="filename">%s'
                                          '</span>' % displayId,
                                          '</li>'
                                          ]
                                         )
                        total += 1
                userFiles.append('</ul></li>')
                out.append(''.join(userFiles))
            if total < store.get_dbSize(session):
                if session.user.has_flag(session,
                                         'info:srw/operation/1/create',
                                         'eadAuthStore'):
                    disabled = ''
                else:
                    disabled = 'disabled="disabled"'
                for s in store:
                    if s.id[s.id.rfind('-') + 1:] not in names:
                        try:
                            displayId = s.id[:s.id.rindex('-')]
                        except:
                            displayId = s.id
                        out.extend(['<li title=deletedUsers>'
                                    '<span>Deleted Users</span>',
                                    '<ul class="hierarchy">',
                                    '<li>',
                                    '<span class="fileops">'
                                    '<input type="%s" name="recid" '
                                    'value="%s" %s/></span>'
                                    '' % (type, s.id, disabled),
                                    '<span class="filename">%s</span>'
                                    '' % displayId,
                                    '</li>'
                                    ]
                                   )
            return out

    #========================================================================    

    def handle(self, req):
        global script, editStore
        form = FieldStorage(req, True)  
        content = None      
        operation = form.get('operation', None)
        if (operation):
            editStore.begin_storing(session)  
            if (operation == 'add'):  
                content = self.add_form(form)   
                self.send_html(content, req)
            elif (operation == 'delete'):
                content = self.delete_component(form)
                self.send_xml(content, req)
            elif (operation == 'save'):
                (content, valid) = self.save_form(form)
                self.send_xml('<wrap><recid>%s</recid><valid>%s</valid></wrap>'
                              '' % (content, valid), req)
            elif (operation == 'deleteRec'):
                content = self.delete_record(form)
            elif (operation == 'discard'):
                content = self.discard_record(form)
                self.send_xml('<recid>%s</recid>' % content, req)
            elif (operation == 'reassign'):
                content = self.reassign_record(form)
                self.send_xml('<recid>%s</recid>' % content, req)
            elif (operation == 'navigate'):
                content = self.navigate(form)
                self.send_html(content, req)
            elif (operation == 'xml'):
                content = self.preview_xml(req, form)
                self.send_xml(content, req)
            elif (operation == 'preview'):
                content = self.preview_file(req)
                self.send_html(content, req)     
            elif (operation == 'checkId'):
                content = self.checkId(form)
                self.send_xml(content, req)
            elif (operation == 'checkEditId'):
                content = self.checkEditId(form)
                self.send_xml(content, req)
            elif (operation == 'getCheckRecStoreId'):
                content = self.getAndCheckRecStoreId(form)
                self.send_xml(content, req)
            elif (operation == 'getCheckId'):
                content = self.getAndCheckId(form)
                self.send_xml(content, req)
            elif (operation == 'validate'):
                content = self.validateField(form)
                self.send_xml(content, req)  
            elif (operation == 'reset'):
                content = self.reset(form)
                self.send_html(content, req)
            elif (operation == 'view'):
                content = self.view_file(form)   
                self.send_fullHtml(content, req)         
            elif (operation == 'submit'):
                content = self.submit(req, form)
            elif (operation == 'edit'):                
                content = self.edit_file(form)
                self.send_fullHtml(content, req) 
            elif (operation == 'load'):
                content = self.load_file(form, req)
                self.send_fullHtml(content, req)             
            elif (operation == 'create'):
                content = self.generate_file(form)
                self.send_fullHtml(content, req) 
            elif (operation == 'local'):
                content = self.upload_local(form)
                self.send_fullHtml(content, req) 
            elif (operation == 'createtemplate'):
                content = self.create_template(form)
                self.send_fullHtml(content, req)
            elif (operation == 'savetemplate'):
                content = self.save_template(form)
                self.send_xml(content, req)
            elif (operation == 'modifytemplate'):
                content = self.modify_template(form)
                self.send_fullHtml(content, req)
            elif (operation == 'discardtemplate'):
                content = self.discard_template(form)
            editStore.commit_storing(session) 
        else:      
            path = req.uri
            location = path[path.rfind('/'):] 

            if location == '/nojavascript.html':
                content = read_file('nojavascript.html')    
            elif location == '/help.html':
                content = read_file('edithelp.html')
            else:
                content = self.show_editMenu()
            htmlNav = ['<a href="/ead/admin/index.html" title="Administration '
                       'Interface Main Menu">Administration</a>',
                       '<a href="/ead/edit/menu.html" title="Edit/Create Menu"'
                       ' class="navlink">Edit/Create Menu</a>',
                       '<a href="/ead/edit/help.html" title="Edit/Create Help"'
                       ' class="navlink">Edit/Create Help</a>']
            repls = {'%REP_NAME%': repository_name,
                     '%REP_LINK%': repository_link,
                     '%REP_LOGO%': repository_logo,
                     '%TITLE%': title_separator.join(self.htmlTitle),
                     '%NAVBAR%': navbar_separator.join(htmlNav),
                     '%CONTENT%': content
                     }
            page = multiReplace(read_file(templatePath), repls)
            # send the display
            self.send_html(page, req)
           
        # End handle() ---------------------------------------------------
        
    # End class EadEditingHandler ----------------------------------------


def build_architecture(data=None):
    global session, serv, db, recordStore, editStore, authStore
    global formTxr, tocTxr, xmlp, assignDataIdFlow, sourceDir, lockfilepath
    #Discover objects
    session = Session()
    session.database = 'db_ead'
    session.environment = 'apache'
    session.user = None
    serv = SimpleServer(session,
                        cheshirePath + '/cheshire3/configs/serverConfig.xml')
    db = serv.get_object(session, 'db_ead')
    baseDocFac = db.get_object(session, 'baseDocumentFactory')
    sourceDir = baseDocFac.get_default(session, 'data')
    del baseDocFac
    recordStore = db.get_object(session, 'recordStore')
    editStore = db.get_object(session, 'editingStore')  
    authStore = db.get_object(session, 'eadAuthStore')
    assignDataIdFlow = db.get_object(session, 'assignDataIdentifierWorkflow')
    # transformers
    xmlp = db.get_object(session, 'LxmlParser')
    formTxr = db.get_object(session, 'formCreationTxr')
    tocTxr = db.get_object(session, 'editingTocTxr')
    lockfilepath = db.get_path(session, 'defaultPath') + '/indexing.lock'
    rebuild = False


def handler(req):
    global rebuild, logfilepath, cheshirePath, eadEditingHandler
    script = req.subprocess_env['SCRIPT_NAME']
    #req.register_cleanup(build_architecture)
    try:
        remote_host = req.get_remote_host(apache.REMOTE_NOLOOKUP)
        # Change directory to where html fragments are
        os.chdir(os.path.join(cheshirePath,
                              'cheshire3',
                              'www',
                              'ead',
                              'html')
                 )
        # Initialise logger object
        lgr = FileLogger(logfilepath, remote_host)
        eadEditingHandler.logger = lgr
        try:
            # Handle request
            eadEditingHandler.handle(req)
        finally:
            try:
                eadEditingHandler.logger.flush()
            except:
                pass
            
            eadEditingHandler.logger = None
            del lgr                                          
    except:
        # Give error info
        req.content_type = "text/html"
        cgitb.Hook(file=req).handle()
    else:
        return apache.OK
    # End handler()


def authenhandler(req):
    global session, authStore, rebuild
    if (rebuild):
        build_architecture()
    pw = req.get_basic_auth_pw()
    un = req.user
    try:
        session.user = authStore.fetch_object(session, un)
    except:
        return apache.HTTP_UNAUTHORIZED    
    if (session.user and
        session.user.password == crypt(pw,
                                       session.user.password)):
        return apache.OK
    else:
        return apache.HTTP_UNAUTHORIZED
    # End authenhandler()


# Some stuff to do on initialisation
rebuild = True
serv = None
session = None
db = None
sourceDir = None
recordStore = None
editStore = None
authStore = None
assignDataIdFlow = None
xmlp = None
formTxr = None
tocTxr = None
lockfilepath = None
logfilepath = editinglogfilepath

# Initialise handler
eadEditingHandler = EadEditingHandler()