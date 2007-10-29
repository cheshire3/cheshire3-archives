#
# Script:    eadAdminHandler.py
# Version:   0.24
# Date:      08 October 2007
# Copyright: &copy; University of Liverpool 2005-2007
# Description:
#            Web interface for administering a cheshire 3 database of EAD finding aids
#            - part of Cheshire for Archives v3
#
# Author(s): JH - John Harrison <john.harrison@liv.ac.uk>
#            CS - Catherine Smith <catherine.smith@liv.ac.uk>
#
# Language:  Python
# Required externals:
#            cheshire3-base, cheshire3-web
#            Py: localConfig.py, htmlFragments.py
#            HTML: adduser.html, adminmenu.html, adminhelp.html, database.html, edituser.html, footer.html, header.html, preview.html, template.ssi, upload.html.
#            CSS: struc.css, style.css
#            Javascript: ead.js, prototype.js
#            Images: c3_black.gif
#                    folderClosed.jpg, folderOpen.jpg folderItem.jpg
#                    closed.gif, open.gif, tBar.gif
#
# Version History:
# 0.01 - 06/12/2005 - JH - Basic administration navigations and menus
#                        - All originally planned operations coded
# 0.02 - 29/01/2006 - JH - Debugging, enhanced error catching and reporting
# 0.03 - 16/02/2006 - JH - HTML Caching improved in line with method used in run.py and eadSearchHandler.py
# 0.04 - 27/02/2006 - JH - Display tweaks for compatibility with improved CSS
# 0.05 - 06/03/2006 - JH - Minor bug fixes in rebuild_database
#                        - Tweaks to XPath validation
# 0.06 - 16/03/2006 - JH - Tweak to display inline with latest CSS
# 0.07 - 04/08/2006 - JH - Brought inline with Cheshire3 changes (Document Facories rather than groups)
#                        - Database, component, cluster rebuilding run successfully in separate threads
# 0.08 - 25/08/2006 - JH - Updates in line with Cheshire3 API delete_record --> remove_record
# 0.09 - 14/09/2006 - JH - More sensible order of doing things when deleting records - for each store: begin/delete/commit
# 0.10 - 20/09/2006 - JH - Operation request handling improved. Looks like pages requests e.g. /ead/admin/files.html
# 0.11 - 12/10/2006 - JH - Reordered indexing, clustering, components to ensure full subject clusters
# 0.12 - 19/10/2006 - JH - Modified upload and delete files to report progess to screen
#                        - debugging in rebuild, reindex
# 0.13 - xx/12/2006 - JH - Preview functionality added
#                        - Different modes for uploading (upload + insert / upload only) and deleting (delete + unindex / delete file only)
# 0.14 - xx/01/2007 - JH - Preview moved to upload form as a new mode
#                        - Some simple user management added
#                        - threading removed from database rebuild - unreliable and errors untraceable
# 0.15 - 21/03/2007 - JH - Catch ObjectDoesNotExistException as well as FileDoesNotExistException (due to Cheshire3 exception change)
# 0.16 - 28/03/2007 - JH - deal with non ascii characters better in file preview
# 0.17 - 01/05/2007 - JH - Clearing existing databases before rebuilding made compatible with latest Cheshire3 way of doing metadata
#                        - Workflows not executing properly in threads - brought back into main thread
# 0.18 - 28/06/2007 - JH - Minor tweaks to upload and unindexing.
#                        - show/hide python traceback added to error page
# 0.19 - 03/07/2007 - JH - a little more debugging...
# 0.20 - 06/08/2007 - CS - Option buttons changed to checkboxes in Admin/Files interface
#                        - Rewrite of rename function in Admin/Files interface to allow for multiple files to be renamed at once
# 0.21 - 09/08/2007 - CS - Rewrite of delete function to enable multiple file deletion and unindexing
#                        - Bug fixing in interfaces and file preview
#                        - Minor changes to files interface - includes change to 'upload.html' and 'adminhelp.html'
# 0.22 - 20/08/2007 - CS - Redesign of Database Menu and navigation added to delete stats result page - includes changes to 'style.css' and 'database.html'
# 0.23 - 27/09/2007 - JH - Rename wwwSearch --> www_utils
# 0.24 - 08/10/2007 - CS - Stats page modified to allow all previous searchHandler logfiles to be viewed
#
#

from eadHandler import *

# script specific globals
script = '/ead/admin/'

class AdminThread(Thread):
    
    def __init__(self):
        Thread.__init__(self)
        self.error = None
        self.finished = None
        
    def run(self):
        try: self.run2()
        except Exception, e: self.error = e
        except: self.error = 'Undeterminable Error'

        
class WorkflowThread(AdminThread):
    session = None
    wf = None
    input = None
    
    def __init__(self, session, wf, input):
        AdminThread.__init__(self)
        self.session = session
        self.wf = wf
        self.input = input
        
    def run2(self):
        self.wf.process(self.session, self.input)


class BuildHtmlThread(AdminThread):
    def run2(self):
        global overescapedAmpRe, toc_cache_url, repository_name, repository_link, repository_logo, script, toc_scripts
        fullTxr = db.get_object(session, 'htmlFullTxr')
        fullSplitTxr = db.get_object(session, 'htmlFullSplitTxr')
        idList = recordStore.fetch_idList(session)
        total = len(idList)
        print "Caching HTML for %d records..." % (total)
        for rec in recordStore:
            recid = rec.id
            print rec.id.ljust(50),
#            # FIXME: rec.size is always 0
#            # small record assumed to be < 100kb ...
#            if (rec.size * 6 < (100 * 1024)):
#                print '[Build at access time - record is really small (approx %d kb)]' % (rec.size*6)
#                continue
            paramDict = {
                    'RECID': recid,
                    'TOC_CACHE_URL': toc_cache_url,
                    '%REP_NAME%':repository_name, 
                    '%REP_LINK%':repository_link,
                    '%REP_LOGO%':repository_logo, 
                    '%TITLE%': 'Display in Full',
                    '%NAVBAR%': '',
            }
        
            path = '%s/%s-1.shtml' % (cache_path, recid)
            rec = recordStore.fetch_record(session, recid)
            
            tmpl = read_file(templatePath)
            anchorPageHash = {}
            if (len(rec.get_xml()) < maximum_page_size * 1024):
                # Nice and short record/component - do it the easy way
                doc = fullTxr.process_record(session, rec)
                # open, read, delete tocfile NOW to avoid overwriting screwups
                try:
                    tocfile = read_file(os.path.join(toc_cache_path, 'foo.bar'))
                    os.remove(os.path.join(toc_cache_path, 'foo.bar'))
                    tocfile = nonAsciiRe.sub(asciiFriendly, tocfile)
                    try: 
                        tocfile = tocfile.encode('utf-8', 'latin-1')
                    except:
                        try:
                            tocfile = tocfile.encode('utf-16')
                        except:
                            pass # hope for the best
                    tocfile = tocfile.replace('RECID', recid)
                    tocfile = overescapedAmpRe.sub('&\g<1>;', tocfile)
                except IOError: tocfile = None
                except: tocfile = '<span class="error">There was a problem whilst generating the Table of Contents</span>'
                
                doc = doc.get_raw()
                try: 
                    tocfile = tocfile.encode('utf-8', 'latin-1')
                except:
                    try:
                        tocfile = tocfile.encode('utf-16')
                    except:
                        pass # hope for the best
                    
                doc = overescapedAmpRe.sub('&\g<1>;', doc)
                doc = doc.replace('PAGE#', '%s/RECID-1.shtml#' % cache_url)
                doc = nonAsciiRe.sub(_asciiFriendly, doc)
                page = tmpl.replace('%CONTENT%', toc_scripts + doc)
                for k, v in paramDict.iteritems():
                    page = page.replace(k, v)
    
                write_file(path, page)
                print '\t[OK]'
            else:
                # Long record - have to do splitting, link resolving etc.
                doc = fullSplitTxr.process_record(session, rec)
                # open, read, and delete tocfile NOW to avoid overwriting screwups
                try:
                    tocfile = read_file(os.path.join(toc_cache_path, 'foo.bar'))
                    os.remove(os.path.join(toc_cache_path, 'foo.bar'))
                    tocfile = nonAsciiRe.sub(_asciiFriendly, tocfile)
                    try: 
                        tocfile = tocfile.encode('utf-8', 'latin-1')
                    except:
                        try:
                            tocfile = tocfile.encode('utf-16')
                        except:
                            pass # hope for the best
                    tocfile = tocfile.replace('RECID', recid)
                except:
                    pass
                        
                doc = doc.get_raw()
                try: doc = doc.encode('utf-8', 'latin-1')
                except: pass # hope for the best!
                # before we split need to find all internal anchors
                anchor_re = re.compile('<a .*?name="(.*?)".*?>')
                anchors = anchor_re.findall(doc)
                pseudopages = doc.split('<p style="page-break-before: always"/>')
                pages = []
                while pseudopages:
                    page = '<div id="padder"><div id="rightcol" class="ead"><div class="pagenav">%PAGENAV%</div>'
                    while (len(page) < maximum_page_size * 1024):
                        page = page + pseudopages.pop(0)
                        if not pseudopages:
                            break
                            
                    # append: pagenav, end rightcol div, end padder div, left div (containing toc)
                    page = page + '<div class="pagenav">%PAGENAV%</div>\n</div>\n</div>\n<div id="leftcol" class="toc"><!--#include virtual="/ead/tocs/RECID.inc"--></div>'
                    pages.append(page)
                    
                start = 0
                for a in anchors:
                    for x in range(start, len(pages)):
                        if (pages[x].find('name="%s"' % a) > -1):
                            anchorPageHash[a] = x + 1
                            start = x                                       # next anchor must be on this page or later
                            
                for x in range(len(pages)):
                    doc = pages[x]
                    # now we know how many real pages there are, generate some page navigation links
                    pagenav = ['<div class="backlinks">']
                    if (x > 0):
                        pagenav.extend(['<a href="%s/%s-1.shtml" title="First page" onclick="setCookie(\'%s-tocstate\', stateToString(\'someId\'))"><img src="/images/fback.gif" alt="First"/></a>' % (cache_url, recid, recid),
                                        '<a href="%s/%s-%d.shtml" title="Previous page" onclick="setCookie(\'%s-tocstate\', stateToString(\'someId\'))"><img src="/images/back.gif" alt="Previous"/></a>' % (cache_url, recid, x, recid)
                                      ])
                    pagenav.extend(['</div>', '<div class="forwardlinks">'])
                    if (x < len(pages)-1):
                        pagenav.extend(['<a href="%s/%s-%d.shtml" title="Next page" onclick="setCookie(\'%s-tocstate\', stateToString(\'someId\'))"><img src="/images/forward.gif" alt="Next"/></a>' % (cache_url, recid, x+2, recid),
                                        '<a href="%s/%s-%d.shtml" title="Final page" onclick="setCookie(\'%s-tocstate\', stateToString(\'someId\'))"><img src="/images/fforward.gif" alt="Final"/></a>' % (cache_url, recid, len(pages), recid)
                                      ])
                    pagenav.extend(['</div>', '<div class="numnav">'])
                    for y in range(len(pages)):
                        if (y == x):
                            pagenav.append('<strong>%d</strong>' % (y+1))
                        else:
                            pagenav.append('<a href="%s/%s-%d.shtml" title="Page %d" onclick="setCookie(\'%s-tocstate\', stateToString(\'someId\'))">%d</a>' % (cache_url, recid, y+1, y+1, recid, y+1))
                    pagenav.append('</div>')
    
                    # now stick the page together and send it back
                    doc = nonAsciiRe.sub(_asciiFriendly, doc)
                    pagex = tmpl.replace('%CONTENT%', toc_scripts + doc)
                    pagex = pagex.replace('%PAGENAV%', '\n'.join(pagenav))
    
                    #resolve internal ref links
                    for k, v in anchorPageHash.iteritems():
                        pagex = pagex.replace('PAGE#%s"' % k, '%s/RECID-%d.shtml#%s"' % (cache_url, v, k))
    
                    # any remaining links were not anchored - encoders fault :( - hope they're on page 1
                    pagex = pagex.replace('PAGE#', '%s/RECID-1.shtml#' % cache_url)
                            
                    for k, v in paramDict.iteritems():
                        pagex = pagex.replace(k, v)
                                
                    write_file('%s/%s-%d.shtml' % (cache_path, recid, x+1), pagex)
                print '\t[OK - %d pages]' % len(pages)
                
            try:
                if anchorPageHash:
                    for k, v in anchorPageHash.iteritems():
                        tocfile = tocfile.replace('PAGE#%s"' % k, '%s/%s-%d.shtml#%s"' % (cache_url, recid, v, k))
    
                    # any remaining links were not anchored - encoders fault :( - hope they're on page 1
                    tocfile = tocfile.replace('PAGE#', '%s/%s-1.shtml#' % (cache_url, recid))
                else:
                    # must all be on 1 page
                    tocfile = tocfile.replace('PAGE#', '%s/%s-1.shtml#' % (cache_url, recid))
    
                write_file(os.path.join(toc_cache_path, recid +'.inc'), tocfile)
                os.chmod(os.path.join(toc_cach_path, recid + '.inc'), 0755)
                        
            except:
                pass
    

class EadAdminHandler(EadHandler):
    
    def __init__(self, lgr):
        EadHandler.__init__(self, lgr)
        self.globalReplacements.update({'SCRIPT': script,
                                       '%SCRIPT%': script
                                       })
        self.htmlTitle.append('Administration')
        self.htmlNav.append('<a href="help.html" title="Administration Help" class="navlink">Admin Help</a>')

    #- end __init__
    
    
    def _get_genericHtml(self, fn):
        global repository_name, repository_link, repository_logo
        html = read_file(fn)
        paramDict = self.globalReplacements
        paramDict.update({'%TITLE%': ' :: '.join(self.htmlTitle)
                         ,'%NAVBAR%': ' | '.join(self.htmlNav)
                         })
        return multiReplace(html, paramDict)
        
    #- end _get_genericHtml()
    
    def _get_timeStamp(self):
        return time.strftime('%Y-%m-%dT%H%M%S')

    def list_users(self):
        global authStore
        self.htmlTitle.append('User Management')
        lines = ['<table>',
                 '<tr class="headrow"><td>Username</td><td>Real Name</td><td>Email Address</td><td>Telephone</td><td>Operations</tr>']
        #uList = authStore.fetch_idList(session)
        self.logger.log(session.user.address)
        idList = authStore.fetch_idList(session)
        for ctr in range(len(idList)):
            uid = idList[ctr]
            user = authStore.fetch_object(session, uid)
            if ((ctr+1) % 2): rowclass = 'odd'
            else:  rowclass = 'even'
            cells = '<td>%s</td><td>%s</td><td>%s</td><td>%s</td>' % (uid, user.realName, user.email, user.tel)
            if (user.id == session.user.id):
                cells = cells + '<td><a href="users.html?operation=edit&amp;userid=%s" class="fileop">EDIT</a></td>' % (uid)
            else:
                cells = cells + '<td>N/A</td>'
            lines.append('<tr class="%s">%s</tr>' % (rowclass, cells))

        lines.extend(['</table><br/>',
                      '<h3 class="bar">Add New User</h3>',
                      read_file('adduser.html'),])
        return '\n'.join(lines)
    #- end list_users()
           
    def _error(self, msg, page=""):
        if (page == 'users.html'):
            self.htmlTitle.append('User Management')
            self.htmlNav.append('<a href="users.html" title="User Management" class="navlink">Users</a>')
        elif (page == 'files.html'):
            self.htmlTitle.append('File Management')
            self.htmlNav.append('<a href="files.html" title="File Management" class="navlink">Files</a>')
        elif (page == 'database.html'):
            self.htmlTitle.append('Database Management')
            self.htmlNav.append('<a href="database.html" title="Database Management" class="navlink">Database</a>')

        self.htmlTitle.append('Error')
        return '<span class="error">%s</span>' % msg
    
    def _modify_userDom(self, userDom, updateHash):
        global authStore
        # manipulate DOM to make changes
        docNode = userDom.documentElement
        for c in docNode.childNodes:
            if (c.nodeType == c.ELEMENT_NODE) and (updateHash.has_key(c.localName)):
                newNode = userDom.createElementNS(None, c.localName)        # create new node
                txtNode = userDom.createTextNode(updateHash[c.localName])    # create new value as text node
                newNode.appendChild(txtNode)                                # add new value text node
                docNode.replaceChild(newNode, c)                            # replace existing node with new one
                del newNode, txtNode, updateHash[c.localName]                # nullify things and pop item from hash
        
        # add any new information
        for k,v in updateHash.iteritems():
            newNode = userDom.createElementNS(None, k)
            txtNode = userDom.createTextNode(v)
            newNode.appendChild(txtNode)
            docNode.appendChild(newNode)
        
        return userDom
    #- end _modify_userDom()
        
    def _submit_userDom(self, id, userDom):
        rec = FtDomRecord(userDom)
        # nasty hacks to get DOM based record accepted
        rec = docParser.process_document(session, StringDocument(rec.get_xml()))
        rec.id = id
        authStore.store_record(session, rec)
        authStore.commit_storing(session)
    #- end _submit_userDom()

    def _confirm_userDetails(self, user):
        return '''
        <table>
            <tr>
              <td>Username: </td>
              <td>%s</td>
            </tr>
            <tr>
              <td>Full Name: </td>
              <td>%s</td>
            </tr>
            <tr>
              <td>Email: </td>
              <td>%s</td>
            </tr>
            <tr>
              <td>Telephone: </td>
              <td>%s</td>
            </tr>
        </table>''' % (user.id, user.realName, user.email, user.tel)
    
    def add_user(self, form):
        if (form.get('submit', None)):
            userid = form.get('userid', None)
            if not userid:
                return self._error('Unable to add user - you MUST supply a username', 'users.html') + read_file('adduser.html')
            try:
                user = authStore.fetch_object(session, userid)
            except:
                # we do want to add this user
                userRec = docParser.process_document(session, StringDocument(new_user_template.replace('%USERNAME%', userid)))
                userDom = userRec.get_dom()
                passwd = form.get('passwd', None)
                # check password
                newHash = {}
                for f in session.user.simpleNodes:
                    if form.has_key(f):
                        newHash[f] = form.getfirst(f)
                passwd1 = form.get('passwd1', None)
                if (passwd1 and passwd1 != ''):
                    passwd2 = form.get('passwd2', None)
                    if (passwd1 == passwd2):
                        newHash['password'] = crypt(passwd1, passwd1[:2])
                    else:
                        return self._error('Unable to add user - passwords did not match.', 'users.html') + read_file('adduser.html')
                else:
                    return self._error('Unable to add user - password not supplied.', 'users.html') + read_file('adduser.html')
                
                # update DOM
                userDom = self._modify_userDom(userDom, newHash)    
                self._submit_userDom(userid, userDom)                    
                user = authStore.fetch_object(session, userid)
                return '<span class="ok">User successfully added.</span>' + self.list_users()
            else:
                return self._error('User with username/id "%s" already exists! Please try again with a different username.' % (userid), 'users.html') + read_file('adduser.html')
                
        return read_file('adduser.html')
    #- end add_user()
    
    def edit_user(self, form):
        global authStore, rebuild
        self.htmlTitle.append('User Management')
        self.htmlTitle.append('Edit')
        self.htmlNav.append('<a href="users.html" title="User Management" class="navlink">Users</a>')
        userid = form.get('userid', session.user.id)
        try:
            user = authStore.fetch_object(session, userid)
        except:
            return self._error('User with id "%s" does not exist!' % (userid), 'users.html')
        else:
            if (form.get('submit', None)):
                userRec = authStore.fetch_record(session, userid)
                userDom = userRec.get_dom()
                passwd = form.get('passwd', None)
                # check password
                if (passwd and crypt(passwd, passwd[:2]) == user.password):
                    newHash = {}
                    for f in user.simpleNodes:
                        if form.has_key(f):
                            newHash[f] = form.getfirst(f)
                    passwd1 = form.get('passwd1', None)
                    if (passwd1 and passwd1 != ''):
                        passwd2 = form.get('passwd2', None)
                        if (passwd1 == passwd2):
                            newHash['password'] = crypt(passwd1, passwd1[:2])
                        else:
                            return self._error('Unable to update details - new passwords did not match.', 'user.html')
                    
                    # update DOM
                    userDom = self._modify_userDom(userDom, newHash)    
                    self._submit_userDom(userid, userDom)                    
                    user = authStore.fetch_object(session, userid)
                    rebuild = True
                    return '<h3 class="bar">Details successfully updated.</h3>' + self._confirm_userDetails(user)
                else:
                    return self._error('Unable to update details - current password missing or incorrect.', 'users.html')
                
            form = read_file('edituser.html').replace('%USERNAME%', userid)
            for f in user.simpleNodes:
                if hasattr(user,f): form = form.replace('%%%s%%' % f, getattr(user,f))
                else: form = form.replace('%%%s%%' % f, '')
            return form
    #- end edit_user()

    def _walk_directory(self, d):
        global script
        # we want to keep all dirs at the top, followed by all files
        outD = []
        outF = []
        filelist = os.listdir(d)
        filelist.sort()
        for f in filelist:
            if (os.path.isdir(os.path.join(d,f))):
                outD.extend(['<li title="%s">%s' % (os.path.join(d,f),f),
                            '<ul class="hierarchy">',
                            '\n'.join(self._walk_directory(os.path.join(d, f))),
                            '</ul></li>'
                            ])
            else:
                fp = os.path.join(d,f)
                outF.extend(['<li>'
                            ,'<span class="fileops"><input type="checkbox" name="filepath" value="%s"/></span>' % (fp)
                            ,'<span class="filename"><a href="files.html?operation=view&amp;filepath=%s" title="View file contents">%s</a></span>' % (cgi_encode(fp), f)
                            ,'</li>'
                            ])

        return outD + outF
    #- end walk_directory()

    def review_records(self, version='full'):
        global sourceDir
        self.htmlTitle.append('File Management')
        out = []
        if (version=='full'):
            header = 'Existing Files'
            fileformsubmits = '''<input type="submit" name="operation" value="rename" onmousedown="op=this.value;"/>            
            <input type="submit" name="operation" value="delete" onmousedown="op=this.value;"/>
            <input type="submit" name="operation" value="unindex + delete" onmousedown="op='unindex';"/>'''
        else :
            fileformsubmits = '''<input type="submit" name="operation" value="%s" onmousedown="op=this.value;"/>''' % version
            header = 'Please select file(s) to %s' % version
        if (version=='full'):
            out.extend(['<h3 class="bar">Upload <a href="/ead/admin/help.html#files_upload" title="What is this?"><img src="/images/whatisthis.gif" alt="[What is this?]"/></a></h3>', 
               read_file('upload.html'), '<br/>'])    
        out.extend(['<script type="text/javascript" src="/javascript/cookies.js"></script>',
               '<script type="text/javascript" src="/javascript/collapsibleLists.js"></script>',
               '''<script type="text/javascript">
               <!--
               function loadPage() {
                   collapseList('sourceDirTree', getCookie('sourceDirTree'), true);
               }
               function unloadPage() {
                   setCookie('sourceDirTree', stateToString('sourceDirTree'))
               }
               -->
               </script>
               ''',
               '<h3 class="bar">%s  <a href="/ead/admin/help.html#existing_files" title="What is this?"><img src="/images/whatisthis.gif" alt="[What is this?]"/></a></h3>' % (header), 
               '<form action="files.html" name="fileops" method="post" onsubmit="return confirmOp();">',
               fileformsubmits,
               '<ul class="unmarked"><li><img src="/images/folderOpen.jpg" alt=""/>' + sourceDir,
               '<ul id="sourceDirTree" class="unmarked">'
               ])
        out.extend(self._walk_directory(sourceDir))
        out.extend(['</li>','</ul>', '</ul>', fileformsubmits, '</form>'])
        self.logger.log('File options')
        return '\n'.join(out)
    #- end review_records()
    
    def _run_thread(self, t, req):
        start = time.time()
        dotcount = 0
        t.start()
        while (t.isAlive() and not t.finished):
            req.write('.')
            dotcount += 1
            if (dotcount % 200 == 0):
                req.write('<br/>')
                
            time.sleep(5)
        
        if t and not t.error:
            (mins, secs) = divmod(time.time() - start, 60)
            (hours, mins) = divmod(mins, 60)
            req.write('<span class="ok">[OK]</span> %dh %dm %ds<br/>' % (hours, mins, secs))
        else:
            req.write('<span class="error">[FAILED]</span> - %s<br/>' % (t.error))

        return t.error
    # end _run_thread()
    
        
    def _parse_upload(self, data):
        if (type(data) == unicode):
            try: data = data.encode('utf-8')
            except:
                try: data = data.encode('utf-16')
                except: pass # hope for the best!
        
        doc = StringDocument(data)
        doc = ppFlow.process(session, doc)
        try:
            rec = docParser.process_document(session, doc)
        except:
            newlineRe = re.compile('(\s\s+)')
            doc.text = newlineRe.sub('\n\g<1>', doc.get_raw())
            # repeat parse with correct line numbers
            try:
                rec = docParser.process_document(session, doc)
            except:
                self.htmlTitle.append('Error')
                e = sys.exc_info()
                self.logger.log('*** %s: %s' % (e[0], e[1]))
                # try and highlight error in specified place
                lines = doc.get_raw().split('\n')
                positionRe = re.compile(':(\d+):(\d+):')
                mo = positionRe.search(str(e[1]))
                line, posn = lines[int(mo.group(1))-1], int(mo.group(2))
                startspace = newlineRe.match(line).group(0)
                return '''\
        <div id="wrapper"><p class="error">An error occured while parsing your file. 
        Please check the file at the suggested location and try again.</p>
        <code>%s: %s</code>
        <pre>
%s
<span class="error">%s</span>
        </pre>
        <p><a href="files.html">Back to file page</a></p></div>
                ''' % (e[0], e[1], html_encode(line[:posn+20]) + '...',  startspace + str('-'*(posn-len(startspace))) +'^')
        
        del data, doc
        return rec
    # end _parse_upload()
        
    def _validate_isadg(self, rec):
        global required_xpaths
        # check record for presence of mandatory XPaths
        missing_xpaths = []
        for xp in required_xpaths:
            try: rec.process_xpath(xp)[0];
            except IndexError:
                missing_xpaths.append(xp)
        if len(missing_xpaths):
            self.htmlTitle.append('Error')
            newlineRe = re.compile('(\s\s+)')
            return '''
    <p class="error">Your file does not contain the following mandatory XPath(s):<br/>
    %s
    </p>
    <pre>
%s
    </pre>
    ''' % ('<br/>'.join(missing_xpaths), newlineRe.sub('\n\g<1>', html_encode(rec.get_xml())))
        else:
            return None

    # end _validate_isadg()
    
    def preview_file(self, form):
        global session, repository_name, repository_link, repository_logo, cache_path, cache_url, toc_cache_path, toc_cache_url, toc_scripts, script, fullTxr, fullSplitTxr
        self.htmlTitle.append('Preview File')
        self.htmlNav.append('<a href="/ead/admin/files.html" title="Preview File" class="navlink">Files</a>')
        f = form.get('eadfile', None)
        pagenum = int(form.getfirst('pagenum', 1))
        if not f or not len(f.value):
            #here make it do all the header stuff too
            return read_file('preview.html')
        
        self.logger.log('Preview requested')
        rec = self._parse_upload(f.value)
        if not isinstance(rec, LxmlRecord):
            return rec
        
        val = self._validate_isadg(rec)
        if (val): return val
        del val
        
        # ensure restricted access directory exists
        try:
            os.makedirs(os.path.join(cache_path, 'preview'))
            os.makedirs(os.path.join(toc_cache_path, 'preview'))
        except OSError:
            pass # already exists

        recid = rec.id = 'preview/%s' % (session.user.username)    # assign rec.id so that html is stored in a restricted access directory
        paramDict = self.globalReplacements
        paramDict.update({'%TITLE%': ' :: '.join(self.htmlTitle)
                         ,'%NAVBAR%': ' | '.join(self.htmlNav)
                         ,'LINKTOPARENT': ''
                         , 'RECID': recid
                         })
        try:
            page = self.display_full(rec, paramDict)[pagenum-1]
        except IndexError:
            return 'No page number %d' % pagenum
        
        if not (os.path.exists('%s/%s.inc' % (toc_cache_path, recid))):
            page = page.replace('<!--#include virtual="%s/%s.inc"-->' % (toc_cache_url, recid), 'There is no Table of Contents for this file.')
        else:
            # cannot use Server-Side Includes in script generated pages - insert ToC manually
            try:
                page = page.replace('<!--#include virtual="%s/%s.inc"-->' % (toc_cache_url, recid), read_file('%s/%s.inc' % (toc_cache_path, recid)))
            except:
                page = page.replace('<!--#include virtual="%s/%s.inc"-->' % (toc_cache_url, recid), '<span class="error">There was a problem whilst generating the Table of Contents</span>')
 
        return page
    #- end preview_file()

    def upload_file(self, req, form):
        self.htmlTitle.append('File Management')
        self.htmlTitle.append('Upload File')
        self.htmlNav.append('<a href="files.html" title="File Management" class="navlink">Files</a>')
        f = form.get('eadfile', None)
        op = form.get('operation', 'insert')
        if not f or not len(f.value):
            #add in return header too etc.
            return read_file('upload.html')
        
        rec = self._parse_upload(f.value)
        # TODO: handle file not successfully parsed
        if not isinstance(rec, LxmlRecord):
            return rec
        
        val = self._validate_isadg(rec)
        if (val): return val
        del val
        
        # setup http headers etc
        req.content_type = 'text/html'
        req.send_http_header()
        head = self._get_genericHtml('header.html')
        req.write(head + '<div id="wrapper">')
        fn = f.filename.split('\\')[-1]
        fnparts = fn.split('.')
        newname = '%s-%s-%s.%s' % ('.'.join(fnparts[:-1]), session.user.username, self._get_timeStamp(), fnparts[-1])
        write_file(os.path.join(sourceDir,newname), f.value)
        req.write('File <code>%s</code> uploaded and stored on server as <code>%s</code><br/>\n' % (f.filename, newname))
        if (op == 'insert'):
            # 'open' all dbs and recordStores
            db.begin_indexing(session)
            recordStore.begin_storing(session)
            dcRecordStore.begin_storing(session)
            
            # index record in thread to allow feedback
            req.write('Loading and Indexing record .')
            t = WorkflowThread(session, indexRecordFlow, rec)
            self._run_thread(t, req)
            if t.error:
                # thread failed to complete - nothing else will work!
                self.logger.log('File upload attempt by %s failed to complete.' % (session.user.username))
                req.write('<span class="error">Parsing/Indexing exited abnormally with message:<br/>\n%s</span>' % t.error)
            else:
                recordStore.commit_storing(session)
                dcRecordStore.commit_storing(session)
                if len(rec.process_xpath('dsc')):
                    req.write('Loading and Indexing components .')
                    compStore.begin_storing(session)
                    # extract and index components
                    t = WorkflowThread(session, compRecordFlow, rec)
                    self._run_thread(t, req)
                    compStore.commit_storing(session)
                
                req.write('Merging indexes ...')
                try:
                    db.commit_indexing(session)
                    db.commit_metadata(session)
                except:
                    req.write('<span class="error">[ERROR]</span> - Could not finish merging indexes. Your record may not be available to search.<br/>\n')
                else:
                    req.write('<span class="ok">[OK]</span><br/>\nUPLOAD + INDEXING COMPLETE')
                    self.logger.log('File Upload: %s added and indexed with id %s' % (newname, rec.id))
        else:
            req.write('UPLOAD COMPLETE')
            self.logger.log('File Upload: %s added' % (newname))
            
        # finish HTML
        req.write('\n<p><a href="/ead/admin/files.html">Back to \'File Management\' page.</a></p>')
        foot = self._get_genericHtml('footer.html')          
        req.write('</div>' + foot)        
        rebuild = True                    # flag for rebuild architecture
        return None 
    #- end upload_file()
    
    
    
    def delete_file(self, req, form):
        self.htmlTitle.append('File Management')
        self.htmlNav.append('<a href="files.html" title="File Management" class="navlink">Files</a>')
        operation = form.get('operation', 'unindex') 
        if (operation == 'unindex + delete'):
            operation = 'unindex'      
        filepaths = form.getlist('filepath')
        # setup http headers etc
        req.content_type = 'text/html'
        req.send_http_header()
        head = self._get_genericHtml('header.html')
        req.write(head + '<div id="wrapper">')     
        if (len(filepaths) == 0):
            return '%s<br />\n<br /><a href="files.html" title="File Management" class="navlink">Back to \'File Management\' Page</a>' % self.review_records(operation)     
        deletedTotal = 0
        unindexedTotal = 0
        errorTotal = 0
        for i, filepath in enumerate(filepaths):
            if not filepath:
                self.htmlTitle.append('Error')
                return 'Could not locate specified file path'     
            # first we have to find the recid by parsing the record
            req.write('Reading original file (<code>%s</code>) ...' % filepath)
            try:
                doc = StringDocument(read_file(filepath))
            except IOError:
                req.write('<span class="error">[ERROR]</span> - File not present on disk<br/>')
            else:
                req.write('<span class="ok">[OK]</span><br/>\nDeleting file from disk ...')
                # remove file
                os.remove(filepath)
                req.write('<span class="ok">[OK]</span><br/>\n')
                deletedTotal += 1;
                self.logger.log('File Delete: %s removed from disk' % (filepath))               
                if (operation == 'unindex'):
                    req.write('Processing...')
                    doc = ppFlow.process(session, doc)
                    rec = docParser.process_document(session, doc)
                    rec = assignDataIdFlow.process(session, rec)
                    recid = rec.id
                    req.write('<br/>\nUnindexing record: %s ...' % recid)
                    try:
                        rec = recordStore.fetch_record(session, recid)
                    except (c3errors.FileDoesNotExistException, c3errors.ObjectDoesNotExistException):
                        # hmm record doesn't exists, simply remove file from disk (already done!)
                        req.write('<span class="error">[ERROR]</span> - Record not present in recordStore<br/>\n')
                        errorTotal += 1
                    else:
                        # delete from indexes
                        db.unindex_record(session, rec)
                        db.remove_record(session, rec)
                        req.write('<span class="ok">[OK]</span><br/>\nDeleting record from stores ...')
                        # delete from recordStore
                        recordStore.begin_storing(session)
                        recordStore.delete_record(session, rec.id)
                        recordStore.commit_storing(session)
                        # delete DC in dcRecordStore
                        dcRecordStore.begin_storing(session)
                        try: dcRecordStore.delete_record(session, rec.id)
                        except: pass
                        else: dcRecordStore.commit_storing(session)
                        req.write('<span class="ok">[OK]</span><br/>\n')
                        
                    if len(rec.process_xpath('dsc')):
                        # now the tricky bit - component records
                        compStore.begin_storing(session)
                        q = CQLParser.parse('ead.parentid exact "%s/%s"' % (rec.recordStore, rec.id))
                        rs = db.search(session, q)
                        req.write('Unindexing %d component records .' % (len(rs)))
                        dotcount = 0
                        for r in rs:
                            try:
                                compRec = r.fetch_record(session)
                            except (c3errors.FileDoesNotExistException, c3errors.ObjectDoesNotExistException):
                                pass
                            else:
                                db.unindex_record(session, compRec)
                                db.remove_record(session, compRec)
                                compStore.delete_record(session, compRec.id)
                            
                            req.write('.')
                            dotcount +=1
                            if (dotcount % 200 == 0):
                                req.write('<br/>')
                    
                        compStore.commit_storing(session)
                        req.write('<span class="ok">[OK]</span><br/>\n')
                    
                    req.write('Merging modified indexes...')
                    try:
                        db.commit_indexing(session)
                    except c3errors.FileDoesNotExistException:
                        # FIXME: R to investigate Cheshire3 quirk
                        req.write('<span class="ok">[OK]</span><br/>\n')
                        unindexedTotal += 1
                    except:
                        req.write('<span class="ok">[INCOMPLETE]</span> - File may still be available until the database is rebuilt.<br/>\n')
                        unindexTotal +=1
                        errorTotal += 1
                    else:
                        req.write('<span class="ok">[OK]</span><br/>\n')
                        db.commit_metadata(session)
                        unindexedTotal += 1
                    self.logger.log('File Delete: %s removed from database' % (rec.id))
                    rebuild = True
        if (operation == 'unindex'):
            req.write('\n<strong>%d file(s) unindexed and deleted</strong>' % unindexedTotal)
        else :
            req.write('\n<strong>%d file(s) deleted</strong>' % deletedTotal)
            req.write('\n<p>Files will remain in the database until the database is rebuilt. This can be done from the <a href="/ead/admin/database.html">\'Database Management\'</a> page</p>')
        if (errorTotal > 0):
            req.write('\n<strong> with %d possible error(s) (see above for details)</strong>' %errorTotal)
        req.write('\n<p><a href="/ead/admin/files.html">Back to \'File Management\' page.</a></p>')
                
        foot = self._get_genericHtml('footer.html')          
        req.write('</div>' + foot)
        return None
    #- end delete_file()
            

    
    def rename_file(self, form):
        global script, rename_notes        
        fileNames = form.getlist('filepath')
        newNames = form.getlist('newname')
        self.htmlTitle.append('File Management')
        self.htmlTitle.append('Rename File')
        self.htmlNav.append('<a href="files.html" title="File Management" class="navlink">Files</a>')
        notes = rename_notes
        #if no file is selected and we have no new names (i.e. are coming from main menu)
        if (len(newNames) == 0 and len(fileNames) == 0):
            return '''%s<br />
                        \n<br />
                        <a href="files.html" title="File Management" class="navlink">Back to \'File Management\' Page</a>
                    ''' % self.review_records('rename')
        #if a file is selected and we have no new names (i.e. are coming from main menu)             
        elif (len(newNames) == 0 and len(fileNames) > 0):             
            fileRename = []          
            for i in range(len(fileNames)):
                xmlSelected = ''
                sgmlSelected = ''
                p = fileNames[i]
                d,base = os.path.split(p)
                fn, ext = os.path.splitext(base)
                if (ext == '.xml'):
                    xmlSelected = ' selected="selected"'
                else :
                    sgmlSelected = ' selected="selected"'                    
                fileRename.append('''<input type="hidden" name="filepath%d" value="%s"/>
                                     <p><strong>%s%s</strong><br />
                                     <input type="text" name="newname" size="50" value="%s"/>
                                     <select name="extension%d">
                                         <option value=".sgml"%s>.sgml</option>
                                         <option value=".xml"%s>.xml</option>
                                     </select>
                              ''' % (i, p, fn, ext, fn, i, sgmlSelected, xmlSelected))
                    
            return '''
            %s
            <form action="files.html" method="post">
                <input type="hidden" name="operation" value="rename"/> 
                %s
                <p><input type="submit" name="submit" value="Submit"/></p>
            </form>''' % (notes, ''.join(fileRename))
            self.logger.log('Rename File: form returned')
        #if we have new names (i.e. are coming from rename interface) we make changes if possible and report actions    
        elif (len(newNames) > 0):
            errorCounter = 0
            #setup the report to detail actions/failures
            self.htmlTitle.append('Action Report')
            errors = ['''<div id="actionReport">
                            <h3 class="redheading">There were errors renaming the following files:</h3>
                            %s
                            <form action="files.html" method="post">
                            <input type="hidden" name="operation" value="rename"/>
                    ''' % notes]
            changedFiles = ['<div id="actionReport"><h3 class="greenheading">The following files were successfully renamed:</h3>']
            for i in range(len(newNames)):
                xmlSelected = ''
                sgmlSelected = ''
                p = form.get('filepath%d' % i, None)
                d,base = os.path.split(p)
                fn, ext = os.path.splitext(base)
                ne = form.get('extension%d' % i, None)
                nn = newNames[i]  
                errorMsg = None
                errorDetail = ''
                if (nn ==fn and ne == ext) :
                    errorMsg = 'New filename not provided.'
                else :
                    if (os.path.exists(os.path.join(d,nn + ne))):
                        errorMsg = 'Filename already exists:' 
                        errorDetail = '<code>%s</code>' % os.path.join(nn + ne)
                        self.logger.log('Rename File: ERROR - %s already exists' % os.path.join(d,nn + ne))
                    else :
                        try :
                            os.rename(p, os.path.join(d,nn + ne))
                        except OSError :
                            errorMsg = 'Directory path does not exist:'
                            errorDetail = '<code>%s</code>' % os.path.join(nn + ne)
                            self.logger.log('Rename File: ERROR - %s directory does not exist' % os.path.join(d,nn + ne)) 
                        else :
                            # log result
                            self.logger.log('Rename File: %s --> %s' % (p, os.path.join(d,nn + ne)))
                            changedFiles.append('<p><code>%s%s</code><span class="ok"> renamed </span><code>%s%s</code><br /></p>' % (fn, ext, nn, ne))
                if (errorMsg):
                    if (ext == '.xml'):
                        xmlSelected = ' selected="selected"'
                    else :
                        sgmlSelected = ' selected="selected"'
                    errors.append('''<input type="hidden" name="filepath%d" value="%s"/>
                                    <p>
                                        <span class="error">%s</span> 
                                        %s<br />
                                        <input type="text" name="newname" size="50" value="%s"/>
                                        <select name="extension%d"><option value=".sgml"%s>.sgml</option><option value=".xml"%s>.xml</option></select>
                                    </p>''' % (errorCounter, p, errorMsg, errorDetail, fn, errorCounter, sgmlSelected, xmlSelected))
                    errorCounter += 1

            output = []
            if (len(changedFiles) > 1): 
                changedFiles.append('</div>')          
                output.append(''.join(changedFiles))
            if (len(errors) > 1):
                errors.append('<p><input type="submit" name="submit" value="Submit"/></form></p></div>')
                output.append(''.join(errors))    
            output.append('<br /><a href="files.html" title="File Management" class="navlink">Back to \'File Management\' Page</a>')
            return ''.join(output)
    #- end rename_file()        
            

    
    def view_file(self, form):

        global script
        self.htmlTitle.append('File Management')

        self.htmlNav.append('<a href="files.html" title="File Management" class="navlink">Files</a>')
        filepath = form.get('filepath', None)
        if not filepath:
            self.htmlTitle.append('Error')
            return 'Could not locate specified file path'

        self.htmlTitle.append('View File')

        out = ['<div class="heading">%s</div>' % (filepath),'<pre>']
        out.append(html_encode(read_file(filepath)))
        out.append('</pre>')

        return '\n'.join(out)
    #- end view_file()

    def _clear_dir(self, dir):
        # function to recursively clear an entire directory - dangerous if used incorrectly!!!
        # imitates "rm -rf dir" in shell
        for f in os.listdir(dir):
            fp = os.path.join(dir, f)
            if os.path.isdir(fp):
                self._clear_dir(fp)
                if fp[-7:] != 'preview':
                    os.rmdir(fp)
            else:
                os.remove(fp)
                
        #- end _clear_dir() --------------------------------------------------------    
    
    def _timeop(self, fn, args=(), kwargs={}):
        start = time.time()
        fn(*args, **kwargs)
        mins, secs = divmod(time.time() - start, 60)
        hours, mins = divmod(mins, 60)
        return (hours, mins, secs)
        

    def rebuild_database(self, req):
        global dbPath, db, sourceDir, baseDocFac, recordStore, dcRecordStore, buildFlow, buildSingleFlow
        global clusDb, clusStore, clusFlow
        global compStore, compFlow, compRecordFlow, rebuild
        # setup http headers etc
        self.htmlTitle.append('Rebuild Database')
        self.htmlNav.append('<a href="database.html" title="Database Management" class="navlink">Database</a>')    
        req.content_type = 'text/html'
        req.send_http_header()
        head = self._get_genericHtml('header.html')
        req.write(head + '<div id="wrapper">')
        req.write('Deleting existing data stores and indexes...')
        # delete main stores, metadata, and indexes
        self._clear_dir(os.path.join(dbPath, 'stores'))
        self._clear_dir(os.path.join(dbPath, 'indexes'))
        self._clear_dir(os.path.join(dbPath, 'cluster', 'stores'))
        self._clear_dir(os.path.join(dbPath, 'cluster', 'indexes'))
        # now we've blitzed everything, we'll have to rediscover/build the objects
        build_architecture()
        # rebuild and reindex
        req.write('<span class="ok">[OK]</span><br/>Loading and Indexing records from <code>%s</code><br/>\n' % sourceDir)
        recordStore.begin_storing(session)
        dcRecordStore.begin_storing(session)
        db.begin_indexing(session)
        # for some reason this doesn't work well in threads...
        start = time.time()
        dotcount = 0
        try:
            baseDocFac.load(session)
            for doc in baseDocFac:
                buildSingleFlow.process(session, doc)
                req.write('.')
                dotcount += 1
                if (dotcount % 200 == 0):
                    req.write('<br/>')
                    
            mins, secs = divmod(time.time() - start, 60)
            hours, mins = divmod(mins, 60)
            req.write('<span class="ok">[OK]</span> %dh %dm %ds<br/>' % (hours, mins, secs))
            recordStore.commit_storing(session)
            dcRecordStore.commit_storing(session)
            db.commit_indexing(session)
            db.commit_metadata(session)
        except:
            # failed to complete - nothing else will work!
            self.logger.log('Database rebuild attempt by %s failed to complete.' % (session.user.username))
            # FIXME: if above not done in thread, need better error message
            #req.write('<span class="error">Indexing exited abnormally with message:<br/>\n%s</span>' % t.error)
            req.write('<span class="error">Indexing exited abnormally</span>')
        else:
            # finish clusters
            req.write('Finishing subject clusters...')
            clusDocFac = db.get_object(session, 'clusterDocumentFactory')
            clusDocFac.load(session, os.path.join(dbPath,'tempCluster.data'))
            session.database = 'db_ead_cluster'
            hours, mins, secs = self._timeop(clusFlow.process, (session, clusDocFac))
            req.write('<span class="ok">[OK]</span> %dh %dm %ds<br/>' % (hours, mins, secs))
            session.database = 'db_ead'
            # rebuild and reindex components
            req.write('Loading and indexing components.')
            hours, mins, secs = self._timeop(compFlow.process, (session, recordStore))
            req.write('<span class="ok">[OK]</span> %dh %dm %ds<br/>\nDATABASE REBUILD COMPLETE' % (hours, mins, secs))
            req.write('<br/>\n<a href="database.html" title="Database Management" class="navlink">Back to \'Database Management\' Page</a>')
            self.logger.log('Database rebuilt by: %s' % (session.user.username))

        # finish HTML, log
        foot = self._get_genericHtml('footer.html')          
        req.write('</div>' + foot)
        rebuild = True
        
        #- end rebuild_database() --------------------------------------------------


    def reindex_database(self, req):
        global dbPath, db, recordStore, compStore, clusDb, clusStore, clusFlow, rebuild
        self.htmlTitle.append('Reindex Database')
        self.htmlNav.append('<a href="database.html" title="Database Operations">Database</a>')
        # setup http headers etc
        req.content_type = 'text/html'
        req.send_http_header()
        head = self._get_genericHtml('header.html')
        req.write(head + '<div id="wrapper">')
        req.write('Deleting existing indexes...')
        # delete existing indexes
        self._clear_dir(os.path.join(dbPath, 'indexes'))
        # delete cluster stores, metadata, and indexes
        self._clear_dir(os.path.join(dbPath, 'cluster', 'stores'))
        self._clear_dir(os.path.join(dbPath, 'cluster', 'indexes'))
        # now we've blitzed everything, we'll have to rediscover/build the objects
        build_architecture()
        req.write('<span class="ok">[OK]</span><br/>Indexing records.')
        db.begin_indexing(session)
        # reindex records
        start = time.time()
        reccount = 0
        problems = []
        for rec in recordStore:
            try: 
                db.index_record(session, rec)
            except Exception, e:
                problems.append((rec.id, e))
                continue
            else:
                req.write('.')
                reccount += 1
                if (reccount % 200 == 0): req.write('<br/>')
        
        mins, secs = divmod(time.time() - start, 60)
        hours, mins = divmod(mins, 60)
        req.write('<span class="ok">[OK]</span> %dh %dm %ds<br/>' % (hours, mins, secs))
        if len(problems):
            req.write('<span class="error">The following record(s) were omitted due to errors that occured while indexing: <br/>\n')
            req.write('<br/>\n'.join(['%s - %r:%r' % (p[0], p[1][0], p[1][1]) for p in problems]))
            req.write('<br/>\n')
                      
        # finish clusters
        req.write('Finishing subject clusters...')
        clusDocFac = db.get_object(session, 'clusterDocumentFactory')
        clusDocFac.load(session, os.path.join(dbPath,'tempCluster.data'))
        session.database = 'db_ead_cluster'
        hours, mins, secs = self._timeop(clusFlow.process, (session, clusDocFac))
        req.write('<span class="ok">[OK]</span> %dh %dm %ds<br/>' % (hours, mins, secs))
        session.database = 'db_ead'
        # reindex components
        req.write('Indexing components.')
        start = time.time()
        dotcount = 0
        # refresh compStore - seems to be busted :?
        compStore = db.get_object(session, 'componentStore')
        for rec in compStore:
            try:
                db.index_record(session, rec)
            except:
                continue
            else:
                dotcount += 1
                if (dotcount % 10 == 0): req.write('.')
                if (dotcount % (200 * 10) == 0): req.write('<br/>')
        
        mins, secs = divmod(time.time() - start, 60)
        hours, mins = divmod(mins, 60)
        req.write('<span class="ok">[OK]</span> %dh %dm %ds<br/>' % (hours, mins, secs))    
        req.write('Merging indexes...')
        start = time.time()
        hours, mins, secs = self._timeop(db.commit_indexing, [session])
        hours2, mins2, secs2 = self._timeop(db.commit_metadata, [session])
        hours+=hours2; mins+=mins2; secs+=secs2
        req.write('<span class="ok">[OK]</span> %dh %dm %ds<br/>\nDATABASE REINDEX COMPLETE' % (hours, mins, secs))
        req.write('<br/>\n<a href="database.html" title="Database Management" class="navlink">Back to \'Database Management\' Page</a>')
        # finish HTML, log
        foot = self._get_genericHtml('footer.html')          
        req.write('</div>' + foot)
        self.logger.log('Database reindexed by: %s' % (session.user.username))
        rebuild = True
        
        #- end reindex_databases() -------------------------------------------------
        
    
    def delete_html(self):
        global cache_path, toc_cache_path
        self.htmlTitle.append('Delete Cached HTML')
        self.htmlNav.append('<a href="database.html" title="Database Operations">Database</a>')
        # delete exisiting HTML
        self._clear_dir(cache_path)
        # don't forget tocs
        self._clear_dir(toc_cache_path)
        self.logger.log('Cached HTML deleted by: %s' % (session.user.username))
        self.htmlTitle.append('Successful')
        return '''<div id="single">Cached HTML copies of records deleted successfully
                    <br />
                        <a href="database.html" title="Database Management" class="navlink">Back to \'Database Management\' Page</a>
                  </div>'''
        #- end delete_html()
    
    
    def rebuild_html(self, req):
        global cache_path, toc_cache_path
        self.htmlTitle.append('Build HTML')
        self.htmlNav.append('<a href="database.html" title="Database Operations">Database</a>')
        # setup http headers etc
        req.content_type = 'text/html'
        req.send_http_header()
        head = self._get_genericHtml('header.html')
        req.write(head + '<div id="wrapper"><div id="single">')
        req.write('Deleting existing HTML...')
        # delete exisiting HTML
        self._clear_dir(cache_path)
        # don't forget tocs
        self._clear_dir(toc_cache_path)
        self.logger.log('Cached HTML deleted by: %s' % (session.user.username))  
        req.write('<span class="ok">[OK]</span><br/>Rebuilding HTML:')
        t = BuildHtmlThread()
        self._run_thread(t,req)
        if not t.error:
            req.write('COMPLETED')
        else:
            req.write('<span class="error">An error occured. HTML may not have been built.<br/>%s</span>' % (t.error))
        req.write('<br /><a href="database.html" title="Database Management" class="navlink">Back to \'Database Management\' Page</a>')
        foot = self._get_genericHtml('footer.html')          
        req.write('</div><!--end single--></div><!--end wrapper-->' + foot)
    
        #- end rebuild_html()
        
        
    def view_statistics(self, file='searchHandler.log'):
        # parse the relevant search logfile and present stats nicely
        global searchlogfilepath, firstlog_re, loginstance_re, timeTaken_re, recid_re, emailRe, logpath
        regex = re.compile('searchHandler\S')
        dateRegex = re.compile('[\S]*-(([\d]*)-([\d]*)-([\d]*))T([\d]{2})([\d]{2})([\d]{2}).log')
        self.logger.log('View Search Statistics')
        self.htmlTitle.append('Search Statistics')
        try: 
            allstring = read_file(logpath + '/' +  file)
        except: 
            self.htmlTitle.append('Error')
            self.logger.log('No logfile present at %s' % (logpath + '/' +  file))
            return 'No logfile present at specified location <code>%s</code>' % (logpath + '/' +  file)
        try: 
            filestarted = firstlog_re.search(allstring).group(1)
        except: 
            #return 'No requests logged in current logfile.'
            filestarted = None
        
        #create list of options for select menu
        files = os.listdir(logpath)
        files.sort(reverse=True)
        options= []
        for f in files :
            if(regex.match(f)):       
                date = re.findall(dateRegex, f)
                if (f == 'searchHandler.log' and f == file):
                    options.append('<option value="%s" selected="true">%s</option>' % (f, 'current'))
                elif (f == 'searchHandler.log'):
                    options.append('<option value="%s">%s</option>' % (f, 'current'))                                    
                elif (f == file):
                    options.append('<option value="%s" selected="true">%s-%s-%s</option>' % (f, date[0][1], date[0][2], date[0][3]))
                else :
                    options.append('<option value="%s">%s-%s-%s</option>' % (f, date[0][1], date[0][2], date[0][3]))
        if (file == 'searchHandler.log'):
            dateString = time.strftime("%Y-%m-%d %H:%M:%S")
        else :
            dateString = '%s %s:%s:%s' % (date[0][0], date[0][4], date[0][5], date[0][6])
            
        #create the html
        rows = ['<div id="leftcol">', 
                '<h3>Statistics for period ending: <select id="fileNameSelect" value="1" onChange="window.location.href=\'statistics.html?fileName=\' + this.value">%s</select></h3>' % ''.join(options)]
        
        if (filestarted != None):
            rows.append('<h3>Period covered: %s to %s</h3>' % (filestarted, dateString))
        else :
            rows.append('<h3>Period covered: None</h3>')
        
        rows.extend(['<table class="stats" width="100%%">',
               '<tr class="headrow"><th>Operation</th><th>Requests</th><th>Avg Time (secs)</th></tr>'])
               
        singlelogs = loginstance_re.findall(allstring)
        ops = {}
        # ops[type] = [log_file_search_string, stats_page_display_name, occurences, total_seconds_taken]
        ops['similar'] = [': Similar Search', 'Similar Search', 0, 0.0]
        ops['search'] = [': Searching CQL query', 'Search', 0, 0.0]
        ops['browse'] = [': Browsing for', 'Browse', 0, 0.0]
        ops['resolve'] = [': Resolving subject', 'Find Subjects', 0, 0.]
        ops['summary'] = [': Summary requested', 'Summary', 0, 0.0]
        ops['full'] = [': Full-text requested', 'Full-text', 0, 0.0]
        ops['email'] = ['emailed to', 'E-mail', 0, 0.0]
        recs = {'full': {}, 'summary': {}, 'email': {}}
        addy_list = []
        # process each log to collate stats
        for s in singlelogs:
            for k in ops.keys():
                if s.find(ops[k][0]) > -1:
                    ops[k][2] += 1
                    ops[k][3] += float(timeTaken_re.search(s).group(1))
                    if k in recs.keys():
                        regex = recid_re[k]
                        recid = regex.search(s).group(1)
                        try: recs[k][recid] += 1
                        except KeyError: recs[k][recid] = 1
                    if k == 'email':
                        addy = emailRe.search(s)
                        if addy and addy.group(0) not in addy_list:
                            addy_list.append(addy.group(0))
              
        # write HTML for stats
        allAvgTime = []
        for op in ops.keys():
            try:
                avgTime = str(round(ops[op][3] / ops[op][2], 3))
                allAvgTime.append(avgTime)
            except ZeroDivisionError:
                avgTime = 'n/a'
                
            rows.append('<tr><td>%s</td><td>%d</td><td>%s</td></tr>' % (ops[op][1], ops[op][2], str(avgTime)))
            if op == 'email':
                rows.append('<tr><td/><td colspan="2"><em>(%d different recipients)</em></td></tr>' % (len(addy_list)))

        rows.extend([
        '<tr><td>Total</td><td>%d</td><td>%s</td></tr>' % (len(singlelogs), 'n/a'),
        '</table>'])
        
        if (file == 'searchHandler.log'):
            rows.extend(['<form action="statistics.html?operation=reset" method="post" onsubmit="return confirm(\'This operation will reset all statistics. The existing logfile will be moved and will be accessible from the drop down menu on the statistics page. Are you sure you want to continue?\');">',
                            '<p><input type="submit" name="resetstats" value=" Reset Statistics "/></p>',
                        '</form>'])

        rows.append('</div>')     
        
        # League tables
        rows.extend([
        '<div id="rightcol">',
        '<h3>Most Requested</h3>',
        '<table width="100%%" summary="Most requested league table">'])
        
        for type, dict in [('Summaries', recs['summary']), ('Full-texts', recs['full']), ('E-mails', recs['email'])]:
            rows.append('<tr class="headrow"><td>%s</td><td>Record Id</td></tr>' % (type))
            sortlist = [((v,k)) for k,v in dict.iteritems()]
            sortlist.sort()
            sortlist.reverse()
            tops = sortlist[:min(5, len(sortlist))]
            for reqs, id in tops:
                rows.append('<tr><td>%d</td><td>%s</td></tr>' % (reqs, id))
                 
        rows.extend(['</table>','</div>'])
        

        return '\n'.join(rows)
        #- end view_statistics() 
    
    
    def reset_statistics(self):
        global logpath, searchlogfilepath
        newfilepath = os.path.join(logpath, 'searchHandler-%s.log' % (self._get_timeStamp()))
        if not os.path.exists(searchlogfilepath): 
            self.htmlTitle.append('Error')
            self.logger.log('No logfile present at %s' % (searchlogfilepath))
            return 'No logfile present at specified location <code>%s</code>' % (searchlogfilepath)
        
        os.rename(searchlogfilepath, newfilepath)
        file(searchlogfilepath, 'w').close()
        self.logger.log('Search Statistics Reset')
        self.htmlTitle.append('Search Statistics')
        return 'Statistics reset. New logfile started. \n<br />\nOld logfiles can still be viewed by selecting them from the drop down box on the statistics page.\n<br />\n<br />\n<a href="/ead/admin/index.html" class="navlink">Back to \'Administration Menu\'</a>'
        #- end reset_statistics()


    def handle(self, req):
        global script
        # read the template in
        tmpl = read_file(templatePath)
        path = req.uri[1:].rsplit('/', 1)[1]
        # get contents of submitted form
        form = FieldStorage(req)
        content = None
        operation = form.get('operation', None)
        self.htmlNav.append('<a href="/ead/admin/index.html" title="Administration Interface Main Menu">Administration</a>')
        directFiles = {'index.html': 'adminmenu.html',
                       'menu.html': 'adminmenu.html',
                       'help.html': 'adminhelp.html'
                       }
                
        try:
            if (directFiles.has_key(path)):
                content = read_file(directFiles[path])
            elif (path == 'users.html'):
                if (operation):
                    if (operation == 'add'):
                        content = self.add_user(form)
                    elif (operation == 'edit'):
                        content = self.edit_user(form)
                    elif (operation == 'logout'):
                        content = self.logout_user(req)
                    else:
                        #invalid operation selected
                        self.htmlTitle.append('Error')
                        content = 'An invalid operation was attempted. Valid operations are:<br/>add, edit.'
                else:
                    content = self.list_users()
            elif (path == 'files.html'):
                # file type operations
                if (operation):
                    if (operation == 'view'):
                        content = self.view_file(form)
                    elif (operation == 'preview'):
                        content = self.preview_file(form)
                        if not (content): 
                            content = read_file(path)
                        else :
                            self.send_html(content, req)
                            return 1
                    elif (operation == 'upload' or operation == 'insert'):
                        content = self.upload_file(req, form)
                        if not content: return
                    elif (operation == 'delete' or operation == 'unindex + delete'):
                        content = self.delete_file(req, form)
                        if not content: return
                    elif (operation == 'rename'):
                        content = self.rename_file(form)
                    else:
                        #invalid operation selected
                        self.htmlTitle.append('Error')
                        content = 'An invalid operation was attempted. Valid operations are:<br/>view, upload, insert, unidex + delete, delete, rename'
                else:
                    content = self.review_records()
                    
            elif (path == 'database.html'):
                # database operations
                if (operation):
                    if (operation == 'rebuild'):
                        self.rebuild_database(req); return
                    elif (operation == 'reindex'):
                        self.reindex_database(req); return
                    elif (operation == 'deletehtml'):
                        content = self.delete_html()
                    elif (operation == 'buildhtml'):
                        content = self.rebuild_html(req); return ''
                    else:
                        self.htmlTitle.append('Error')
                        content = 'An invalid operation was attempted. Valid operations are:<br/>rebuild, reindex, deletehtml, buildhtml'
                else:
                    content = read_file('database.html')
                    
            elif (path == 'statistics.html'):
                # statistics reporting
                if (operation):
                    if (operation =='reset'):
                        content = self.reset_statistics()
                    else:
                        self.htmlTitle.append('Error')
                        content = 'An invalid operation was attempted. Valid operations are:<br/>reset'
                else:    
                    content = self.view_statistics(form.get('fileName', 'searchHandler.log'))                
            elif (len(path)):
                # 404
                self.htmlTitle.append('Page Not Found')
                content = '<p>Could not find your requested page: "%s"</p>' % path            
            
        except Exception:
            self.htmlTitle.append('Error')
            cla, exc, trbk = sys.exc_info()
            excName = cla.__name__
            try:
                excArgs = exc.__dict__["args"]
            except KeyError:
                excArgs = str(exc)
                
            self.logger.log('*** %s: %s' % (excName, excArgs))
            excTb = traceback.format_tb(trbk, 100)
            content = '''\
            <div id="wrapper"><p class="error">An error occured while processing your request.<br/>
            The message returned was as follows:</p>
            <code>%s: %s</code>
            <p><strong>Please try again, or contact the system administrator if this problem persists.</strong></p>
            <p>Debugging Traceback: <a class="jscall" onclick="toggleShow(this, 'traceback');">[ show ]</a></p>
            <div id="traceback">%s</div>
            </div>
            ''' % (excName, excArgs, '<br/>\n'.join(excTb))
            
        if not content:
            # return the home/quick search page
            content = read_file('adminmenu.html')
            self.logger.log('Administration options')
            
        content = '<div id="wrapper">%s</div>' % (content)
        page = multiReplace(tmpl, {'%REP_NAME%': repository_name,
                     '%REP_LINK%': repository_link,
                     '%REP_LOGO%': repository_logo,
                     '%TITLE%': ' :: '.join(self.htmlTitle),
                     '%NAVBAR%': ' | '.join(self.htmlNav),
                     '%CONTENT%': content
                     })

        # send the display
        self.send_html(page, req)
        #- end handle()

    #- end class EadAdminHandler

#- Some stuff to do on initialisation
session = None
serv = None
db = None
dbPath = None
# ingest
baseDocFac = None
sourceDir = None
docParser = None
# stores
authStore = None
recordStore = None
dcRecordStore = None
compStore = None
resultSetStore = None
# clusters
clusDb = None
clusStore = None
# transformers
summaryTxr = None
fullTxr = None
fullSplitTxr = None
textTxr = None
# workflows
ppFlow = None
buildFlow = None
buildSingleFlow = None
indexRecordFlow = None
assignDataIdFlow = None
normIdFlow = None
clusFlow = None
compFlow = None
compRecordFlow = None
# other
exactExtracter = None
diacriticNormaliser = None

rebuild = True

def build_architecture(data=None):
    # data argument provided for when function run as clean-up - always None
    global session, serv, db, dbPath, baseDocFac, sourceDir, docParser, \
    authStore, recordStore, dcRecordStore, compStore, resultSetStore, \
    clusDb, clusStore, clusFlow, \
    summaryTxr, fullTxr, fullSplitTxr, textTxr, \
    ppFlow, buildFlow, buildSingleFlow, indexRecordFlow, assignDataIdFlow, normIdFlow, compFlow, compRecordFlow, \
    exactExtracter, diacriticNormaliser, \
    rebuild
    
    # globals line 1: re-establish session; maintain user if possible
    if (session): u = session.user
    else: u = None
    session = Session()
    session.database = 'db_ead'
    session.environment = 'apache'
    session.user = u
    serv = SimpleServer(session, os.path.join(cheshirePath, 'cheshire3', 'configs', 'serverConfig.xml'))
    db = serv.get_object(session, 'db_ead')
    dbPath = db.get_path(session, 'defaultPath')
    baseDocFac = db.get_object(session, 'baseDocumentFactory')
    sourceDir = baseDocFac.get_default(session, 'data')
    docParser = db.get_object(session, 'LxmlParser')
    # globals line 2: stores
    authStore = db.get_object(session, 'eadAuthStore')
    recordStore = db.get_object(session, 'recordStore')
    dcRecordStore = db.get_object(session, 'eadDcStore')
    compStore = db.get_object(session, 'componentStore')
    resultSetStore = db.get_object(session, 'eadResultSetStore'); resultSetStore.clean(session) # clean expires resultSets 
    # globals line 3: subject clusters
    session.database = 'db_ead_cluster'
    clusDb = serv.get_object(session, 'db_ead_cluster')
    clusStore = clusDb.get_object(session, 'eadClusterStore')
    clusFlow = clusDb.get_object(session, 'buildClusterWorkflow'); clusFlow.load_cache(session, clusDb) 
    session.database = 'db_ead'
    # globals line 4: transformers
    summaryTxr = db.get_object(session, 'htmlSummaryTxr')
    fullTxr = db.get_object(session, 'htmlFullTxr')
    fullSplitTxr = db.get_object(session, 'htmlFullSplitTxr')
    textTxr = db.get_object(session, 'textTxr')
    # globals line 5: workflows
    ppFlow = db.get_object(session, 'preParserWorkflow'); ppFlow.load_cache(session, db)
    buildFlow = db.get_object(session, 'buildIndexWorkflow'); buildFlow.load_cache(session, db)
    buildSingleFlow = db.get_object(session, 'buildIndexSingleWorkflow'); buildSingleFlow.load_cache(session, db)
    indexRecordFlow = db.get_object(session, 'indexRecordWorkflow'); indexRecordFlow.load_cache(session, db)
    assignDataIdFlow = db.get_object(session, 'assignDataIdentifierWorkflow'); assignDataIdFlow.load_cache(session, db)
    normIdFlow = db.get_object(session, 'normalizeDataIdentifierWorkflow'); normIdFlow.load_cache(session, db)
    compFlow = db.get_object(session, 'buildAllComponentWorkflow'); compFlow.load_cache(session, db)
    compRecordFlow = db.get_object(session, 'buildComponentWorkflow'); compRecordFlow.load_cache(session, db)
    # globals line 6: other
    exactExtracter = db.get_object(session, 'ExactExtracter')
    diacriticNormaliser = db.get_object(session, 'DiacriticNormaliser')
    
    rebuild = False

logfilepath = adminlogfilepath


def handler(req):
    req.register_cleanup(build_architecture)
    try:
#        if rebuild:
#            build_architecture()
#        else:
#            try:
#                fp = recordStore.get_path(session, 'databasePath')    # attempt to find filepath for recordStore
#                assert (os.path.exists(fp) and time.time() - os.stat(fp).st_mtime > 60*60)
#            except:
#                # architecture not built
#                build_architecture()

        remote_host = req.get_remote_host(apache.REMOTE_NOLOOKUP)                   # get the remote host's IP for logging
        os.chdir(os.path.join(cheshirePath, 'cheshire3','www','ead','html'))        # cd to where html fragments are
        lgr = FileLogger(logfilepath, remote_host)                                  # initialise logger object
        eadAdminHandler = EadAdminHandler(lgr)                                      # initialise handler - with logger for this request
        try:
            eadAdminHandler.handle(req)                                             # handle request
        finally:
            # clean-up
            try: lgr.flush()                                                        # flush all logged strings to disk
            except: pass
            del lgr, eadAdminHandler                                                # delete handler to ensure no state info is retained
            
    except:
        req.content_type = "text/html"
        cgitb.Hook(file = req).handle()                                            # give error info
    else:
        return apache.OK


def authenhandler(req):
    global session, authStore, rebuild
    if (rebuild):
        build_architecture()                                                    # build the architecture
    pw = req.get_basic_auth_pw()
    user = req.user
    try: session.user = authStore.fetch_object(session, user)
    except: return apache.HTTP_UNAUTHORIZED    
    if (session.user and session.user.password == crypt(pw, pw[:2])):
        return apache.OK
    else:
        return apache.HTTP_UNAUTHORIZED
#- end authenhandler()

