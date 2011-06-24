#!/usr/bin/env python
"""

Kukkaisvoima a lightweight weblog system.

Copyright (C) 2006-2011 Petteri Klemola

Kukkaisvoima is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License version 3
as published by the Free Software Foundation.

Kukkaisvoima is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with Kukkaisvoima.  If not, see
<http://www.gnu.org/licenses/>.

"""

import cgi
import pickle
import os
from urllib import quote_plus, unquote_plus
from time import localtime, strptime, strftime
from sets import Set
from datetime import datetime, timedelta
import cgitb; cgitb.enable()
import smtplib
from email.MIMEText import MIMEText
import re
import locale
import random
# kludge to get md5 hexdigest working on all python versions. Function
# md5fun should be used only to get ascii like this
# md5fun("kukkaisvoima").hexdigest()
try:
    from hashlib import md5 as md5fun
except ImportError: # older python (older than 2.5) does not hashlib
    import md5
    md5fun = md5.new


# Config variables
# Url of the blog (without trailing /)
baseurl = 'http://yourdomain/blog/index.cgi'
blogname = 'Kukkaisvoima'
slogan = 'Default installation'
description = "Jee"
encoding = 'iso-8859-15'
# Use absolute url for this
stylesheet = 'kukka.css'
defaultauthor = 'You'
favicon = 'http://yourdomain/favicon.ico'
doctype = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
# Email to send comments to
blogemail = 'you@yourdomain'
# Language for the feed
language = 'en'
# Number of entries per page
numberofentriesperpage = 10
# Directory which contains the blog entries
datadir = '.'
# Directory which contains the index and comments. Must be script
# writable directory
indexdir = 'temp'
# Maximum comments per entry. Use -1 for no comments and 0 for no
# restriction
maxcomments = 30
# answer to spamquestion (question variable is l_nospam_question)
nospamanswer = '5'
# This is admin password to manage comments. password should be
# something other than 'password'
passwd = 'password'
# New in version 10
sidebarcomments = True
# Gravatar support (picture in comments according to email), see
# http://gravatar.com for more information
gravatarsupport = True
# Entry and comment Date format
dateformat = "%F %T"
# Show only first paragraph when showing many entries
entrysummary = False

# Language variables
l_archives = 'Archives'
l_categories = 'Categories'
l_comments = 'Comments'
l_comments2 = 'Comments'
l_date = 'Date'
l_nextpage = 'Next page'
l_previouspage = 'Previous page'
l_leave_reply = 'Leave reply'
l_no_comments_allowed = 'No comments allowed'
l_no_comments = 'No comments'
l_name_needed = 'Name (needed)'
l_email_needed = 'Email (needed)'
l_webpage = 'Webpage'
l_no_html = 'No html allowed in reply'
l_nospam_question = 'What\'s 2 + 3?'
l_delete_comment = 'Delete comment'
l_passwd = 'Admin password'
l_admin = 'Admin'
l_admin_comments = 'Manage comments'
l_do_you_delete = 'Your about to delete comment this, are you sure you want to that?'
# new in version 8
l_search = "Search"
l_search2 = "No matches"
# new in version 10
l_recent_comments = "Recent comments"
l_notify_comments= "Notify me of follow-up comments via email."
# new in version 11
l_read_more = "..."


# import user settings
from kukkaisvoima_settings import *

# version
version = '11dev'

# for date collisions
dates = {}

def generateDate(fileName):
    name, date, categories = fileName[:-4].split(':')
    mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime = os.stat(fileName)
    filedate= datetime(*localtime(mtime)[0:6])
    date = "%s %s:%s:%s" % (date,
                            filedate.hour,
                            filedate.minute,
                            filedate.second)
    try:
        date = datetime(*strptime(
                date,'%Y-%m-%d %H:%M:%S')[0:6])
    except:
        date = filedate
    # if date collision happens add seconds to date
    if dates.has_key(date) and not dates[date] == fileName:
        while dates.has_key(date):
            date += timedelta(seconds=1)
    dates[date] = fileName
    return date

def sendEmail(to, subject, message):
    msg = MIMEText(_text=wrapEmail(message), _charset='%s' % encoding)
    msg['subject'] = subject
    sender = 'Kukkaisvoima blog (%s) <%s>' % (baseurl, blogemail)
    s = smtplib.SMTP()
    s.connect()
    s.sendmail(sender, to, msg.as_string())
    s.close()

def wrapEmail(text):
    """Wrap some lines. Long words with no spaces are preserved."""
    lines = text.splitlines()
    newlines = list()
    for line in lines:
        if line == '':
            newlines.append('')
        while len(line) > 0:
            if len(line) < 73:
                newlines.append(line)
                line = ''
            else:
                nline = line.rfind(' ',0,72)
                if nline == -1:
                    newlines.append(line)
                    line = ''
                else:
                    nline = nline+1
                    newlines.append(line[:nline])
                    line = line[nline:]
    return '\n'.join(newlines)


def removeHtmlTags(line):
    """Removes html tags from line, works also for partial tags, so
    all < > will be removed.
    """
    while line.find("<") > -1 or line.find(">") > -1:
        # there are still tags
        start = line.find("<")
        end = line.find(">")
        if start > -1:
            # found start tag. Search for end
            tmpline = line[start+1:]
            end = tmpline.find(">")
            if end > -1:
                # found end, remove in between
                line = line[:start] + line[start+end+2:]
            else:
                # no end found remove until end of line
                line = line[:end]
        elif end > -1:
            # found > without < tag is open. remove start of the line
            line = line[end+1:]
    return line


class Comment:
    urlre = re.compile('(http|https|ftp)://([A-Za-z0-9/:@_%~#=&\.\-\?\+]+)')
    def __init__(self, author, email, url, comment, subscribe):
        self.author = author
        self.email = email
        self.url = url
        self.comment = comment
        self.date = datetime.now()
        self.subscribe = subscribe
        random.seed()
        self.id = "%016x" % random.getrandbits(128)

    def getUrl(self):
        url = self.url
        if not url:
            return None
        if not url.startswith('http://'):
            url = 'http://%s' % url
        return url

    def getAuthorLink(self):
        url = self.getUrl()
        if url is None:
            return "%s" % self.author
        else:
            return "<a href=\"%s\"  rel=\"external nofollow\">%s</a>"\
                % (url, self.author)

    def getText(self):
        comment = str(self.comment)
        comment = self.comment.replace('\r\n','<br />')
        comment = self.urlre.sub(r'<a href="\1://\2">\1://\2</a>',
                                 comment)
        return comment

    def getEmailMd5Sum(self):
        return md5fun(self.email.lower()).hexdigest()

    def getSubEmail(self):
        try:
            if self.subscribe is None:
                return None
            else:
                return self.email
        except:
            return None

    def getId(self):
        try:
            return self.id
        except:
            return None


def pickleComment(author, email, url, comment, filename, indexdir, subscribe):
    filename = filename.replace('/', '').replace('\\', '')
    filename = "%s.txt" % filename
    # read the old comments
    comments = list()
    try:
        oldcommentsfile = open(os.path.join(indexdir,'comment-%s' % filename), 'rb')
        comments = pickle.load(oldcommentsfile)
        oldcommentsfile.close()
    except:
        pass
    comm = Comment(author, email, url, comment, subscribe)
    comments.append(comm)
    commentfile = open(os.path.join(indexdir,'comment-%s' % filename), 'wb')
    pickle.dump(comments, commentfile)
    commentfile.close()
    updateCommentList()
    return comm


def getComments(filename):
    comments = list()
    comm_file = os.path.join(indexdir,'comment-%s' % filename)
    if os.path.exists(comm_file) is False:
        return comments
    try:
        oldcommentsfile = open(comm_file, 'rb')
        comments = pickle.load(oldcommentsfile)
        oldcommentsfile.close()
    except:
        pass
    return comments


def deleteComment(filename, commentnum):
    comments = getComments(filename)
    comments.pop(commentnum-1)
    commentfile = open(os.path.join(indexdir,'comment-%s' % filename), 'wb')
    pickle.dump(comments, commentfile)
    commentfile.close()
    updateCommentList()
    return


def unsubscribeComments(filename, unsubscribe_id):
    comments = getComments(filename)
    for comment in comments:
        if unsubscribe_id == comment.getId():
            comment.subscribe = None
    commentfile = open(os.path.join(indexdir,'comment-%s' % filename), 'wb')
    pickle.dump(comments, commentfile)
    commentfile.close()


def getCommentList():
    """Gets list of comments from the comment index"""
    commentlist = list()

    # generate list of comments if it does not exist
    if os.path.exists(os.path.join(indexdir,'recent_comments.index')) is False:
        updateCommentList()
    try:
        comindex = open(os.path.join(indexdir,'recent_comments.index'), 'rb')
        commentlist = pickle.load(comindex)
        comindex.close()
    except:
        pass
    return commentlist


def updateCommentList():
    """Updates latest comments list"""
    commentlist = list()
    commentlist_tmp = list()

    for cfile in [x for x in os.listdir(indexdir) if x.startswith("comment-")]:
        cfile = cfile.replace("comment-", "", 1)
        num = 1
        comments = list()
        for cm in getComments(cfile):
            comments.append((cfile, cm, num))
            num += 1
        commentlist_tmp += comments
        # sort and leave 10 latests
        commentlist_tmp.sort(key=lambda com: com[1].date, reverse=True)
        commentlist_tmp = commentlist_tmp[:10]

    for c in commentlist_tmp:
        # get subject from commented entry
        entry = Entry(c[0], datadir)
        commentlist.append({"authorlink" : c[1].getAuthorLink(),
                            "file" : c[0],
                            "num" : c[2],
                            "author" : c[1].author,
                            "subject" : entry.headline})

    commentfile = open(os.path.join(indexdir,'recent_comments.index'), 'wb')
    pickle.dump(commentlist, commentfile)
    commentfile.close()


def getSubscribedEmails(comments):
    """Get list of email subscriptions from comment list. No
       duplicate email"""
    emails = dict()
    for com in comments:
        email = com.getSubEmail()
        if email:
            emails[email] = com.getId()
    return emails


def handleIncomingComment(fs):
    """Handles incoming comment and returns redirect location when
       successful and None in case of an error"""
    author = fs.getvalue('author')
    email = fs.getvalue('email')
    url = fs.getvalue('url')
    comment = fs.getvalue('comment')
    name = fs.getvalue('name')
    commentnum = fs.getvalue('commentnum')
    headline = fs.getvalue('headline')
    nospam = fs.getvalue('nospam')
    subscribe = fs.getvalue('subscribe')
    filename = "%s.txt" % name
    comments_for_entry = getComments(filename)

    # save and send only valid comments
    if (author and email and comment and \
            name and commentnum and \
            maxcomments > -1 and \
            len(comments_for_entry) < maxcomments and \
            nospam == nospamanswer) is False:
        return None

    # remove html tags
    comment = comment.replace('<','[')
    comment = comment.replace('>',']')

    # only one subscription per email address
    if subscribe and \
            email in getSubscribedEmails(comments_for_entry).keys():
        subscribe = None

    new_comment = \
        pickleComment(author, email, url, comment, name, indexdir, subscribe)

    comm_url = new_comment.getUrl()
    if comm_url:
        comm_url = "\nWebsite: %s" % comm_url
    else:
        comm_url = ""

    email_subject = 'New comment in %s' % headline
    email_body = 'Name: %s%s\n\n%s\n\nlink:\n%s/%s#comment-%s' \
        % (author, comm_url, comment, baseurl, name, commentnum)

    # notify blog owner and comment subscribers about the
    # new comment. Email sending may fail for some reason,
    # so try sending one email at time.
    try:
        email_body_admin = email_body
        if subscribe:
            email_body_admin += \
                "\n\nNote: commenter subscribed (%s) to follow-up comments" \
                % email
        sendEmail(blogemail, email_subject, email_body_admin)
    except:
        pass # TODO log errors, for now just fail silently

    # add disclaimer for subscribers
    email_body += \
        "\n\n******\nYou are receiving this because you have signed up for email notifications. "

    email_and_id = getSubscribedEmails(comments_for_entry)
    for subscribe_email in email_and_id.iterkeys():
        comm_id = email_and_id[subscribe_email]
        try:
            email_body_comment = email_body
            email_body_comment += \
                "Click here to unsubscribe instantly: %s/%s?unsubscribe=%s\n" \
                % (baseurl, name, comm_id)
            sendEmail(subscribe_email, email_subject, email_body_comment)
        except:
            pass # TODO log errors, for now just fail silently

    # redirect
    return 'Location: %s/%s#comment-%s\n' % (baseurl, name, commentnum)

class Entry:
    firstpre = re.compile("<p.*?(</p>|<p>)", re.DOTALL | re.IGNORECASE)
    whitespacere = re.compile("\s")
    def __init__(self, fileName, datadir):
        self.fileName = fileName
        self.fullPath = os.path.join(datadir, fileName)
        self.text = open(self.fullPath).readlines()
        self.text = [line for line in self.text if not line.startswith('#')]
        self.headline = self.text[0]
        self.text = self.text[1:]
        self.author = defaultauthor
        self.cat = ''
        name, date, categories = fileName[:-4].split(':')
        self.cat = categories.split(',')
        self.date = generateDate(self.fullPath)
        self.comments = getComments(self.fileName)
        self.url = "%s/%s" % (baseurl,
                              quote_plus(self.fileName[:-4]))

    def getFirstParagraph(self):
        # look for <p>
        text_as_str = "".join(self.text)
        m = self.firstpre.search(text_as_str)
        if m is not None:
            there_is_more = False
            there_is_more_str = "<a href=\"%s\">%s</a>" % \
                (self.url, l_read_more)
            first_paragraph = m.group().split("\n")
            text_as_str = re.sub(self.whitespacere, '', text_as_str)
            first_paragraph_as_string = re.sub(self.whitespacere, '', m.group())
            lastline = first_paragraph.pop()
            lastline.strip()
            if len(text_as_str) > len(first_paragraph_as_string):
                there_is_more = True
            if there_is_more and lastline.lower().endswith("</p>"):
                lastline = lastline[:-4] # removes the </p>
                there_is_more_str = there_is_more_str + "</p>"
            if there_is_more: # and tip that there is still more to this entry
                lastline = lastline + there_is_more_str
            first_paragraph.append(lastline)
            return first_paragraph
        else:
            return self.text

    def getText(self, summary):
        if summary == True:
            return self.getFirstParagraph()
        else:
            return self.text


class Entries:
    def __init__(self, indexdir):
        self.date = {}
        self.categories = {}
        self.indexdir = indexdir

    def add(self, entry):
        self.date[entry.date] = entry
        for cat in entry.cat:
            if self.categories.has_key(cat):
                self.categories[cat][entry.date] = entry
            else:
                self.categories[cat] = {}
                self.categories[cat][entry.date] = entry

    def getOne(self, name):
        x = list()
        x.append(Entry(name, datadir))
        return x

    def getMany(self, pagenumber=0, cat=None):
        indexfile = 'main.index'
        if cat is not None:
            indexfile = '%s.index' % cat
        indexindexfile = open(os.path.join(self.indexdir, indexfile), 'rb')
        indexindex = pickle.load(indexindexfile)
        indexindexfile.close()
        # load the files
        ents = list()
        swd = indexindex.keys()
        swd.sort()
        swd.reverse()
        if pagenumber == -1: # no limit
            pass
        elif pagenumber > 0:
            sindex = numberofentriesperpage*pagenumber
            eindex = (numberofentriesperpage*pagenumber)+numberofentriesperpage
            swd = swd[sindex:eindex]
        else:
            swd = swd[:numberofentriesperpage]
        for key in swd:
            ents.append(Entry(indexindex[key], datadir))
        return ents

def renderHtmlFooter():
    print "<div id=\"footer\">Powered by <a href=\"http://23.fi/kukkaisvoima\">Kukkaisvoima</a> version %s</div>" % version
    print "</div>" # content1
    print "</body>"
    print "</html>"

def renderHtmlHeader(title=None, links=[]):
    print  "Content-Type: text/html; charset=%s\n" % encoding
    print doctype
    print "<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"%(lang)s\" lang=\"%(lang)s\">" % {'lang':language}
    print "<head>"
    if title:
        print "<title>%s | %s - %s</title>" % (title, blogname, slogan)
    else:
        print "<title>%s - %s </title>" % (blogname, slogan)
    print "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=%s\" />" % encoding
    print "<link rel=\"stylesheet\" href=\"%s\" type=\"text/css\" />" % stylesheet
    print "<link rel=\"shortcut icon\" href=\"%s\"/>" % favicon
    print "<link rel=\"alternate\" type=\"application/rss+xml\" title=\"%s RSS Feed\" href=\"%s/feed/\" />" % (blogname, baseurl)

    # print additional links
    for i in links:
        print i

    # Javascript. Used to validate comment form, nice eh :P
    print """
          <script type="text/javascript">
          function validate_not_null(field, msg)
          {
              if (field.value == null || field.value == "")
              {
                  alert(msg);
                  return false;
              }
              return true;
          }

          function validate_email(field, msg)
          {
              at_index = field.value.indexOf("@");
              if ((at_index > 1) && (field.value.lastIndexOf(".") > at_index))
              {
                  return true;
              }
              alert(msg);
              return false;
          }

          function validate_nospam(field, msg)
          {
              if (field.value == "%s")
              {
                  return true;
              }
              alert(msg);
              return false;
          }

          function validate_form(thisform)
          {
              with (thisform)
              {
                  if (validate_not_null(author, "Name must be filled in") == false)
                  {
                      author.focus();
                      return false;
                  }
                  if (validate_email(email,"Email must be filled in and must be valid!") == false)
                  {
                      email.focus();
                      return false;
                  }
                  if (validate_nospam(nospam, "Wrong answer!") == false)
                  {
                      nospam.focus();
                      return false;
                  }
                  if (validate_not_null(comment, "Comment cannot be empty") == false)
                  {
                      comment.focus();
                      return false;
                  }
              }
          }
          </script>
    """ % (nospamanswer)
    print "</head>"
    print "<body>"

    print "<div id=\"content1\">"
    print "<div id=\"header\">"
    print "<h1><a href=\"%s\">%s</a></h1>" % (baseurl, blogname)
    print "<div id=\"slogan\">%s</div>" % slogan
    print "</div>" #header


def renderEntryLinks(entries, text=None):
    for entry in entries:
        link = "<li><a href=\"%s\">%s</a>" % (
            entry.url, entry.headline)
        index = 1
        for cat in entry.cat:
            link += "%s" % cat
            if index != len(entry.cat):
                link += ", "
            index += 1
        link += " (%s)" % entry.date
        if text:
            link += "<br /><pre>%s</pre>" % text
        link += "</li>"
        print link


def renderCategories(catelist, ent, path):
    renderHtmlHeader("archive")
    print "<div id=\"content3\">"

    if len(path) == 1 and path[0] == "categories":
        sortedcat = catelist.keys()
        try:
            sortedcat.sort(key=locale.strxfrm)
        except: # python < 2.4 fails
            sortedcat.sort()
        print "<h2>%s</h2>" % l_categories
        print "<ul>"

        for cat in sortedcat:
            print "<li><a href=\"%s/%s\">%s</a> (%s)</li>" % (
                baseurl, quote_plus(cat), cat, len(catelist[cat]))
            print "<ul>"
            renderEntryLinks(ent.getMany(-1, cat))
            print "</ul>"

        print "</ul>"
    elif len(path) == 2 and path[1] in catelist.keys():
            print "<h2>%s</h2>" % path[1]
            renderEntryLinks(ent.getMany(-1, path[1]))

    print "</div>" # content3
    renderHtmlFooter()
    return


def renderArchive(ent):
    renderHtmlHeader(l_archives)
    print "<div id=\"content3\">"

    print "<h2>%s</h2>" % l_archives
    print "<ul>"
    renderEntryLinks(ent.getMany(-1))
    print "</ul>"

    print "</div>" # content3
    renderHtmlFooter()
    return


def renderSearch(filelist, ent, searchstring):
    renderHtmlHeader(l_search)
    print "<div id=\"content3\">"

    # Remove some special character so that one don't exhaust the web
    # host with stupid .*? searches
    for i in ".^$*+?{[]\|()":
        searchstring = searchstring.replace(i,"")

    pattern = re.compile(searchstring, re.IGNORECASE)

    matchedfiles = {}
    for file in filelist.itervalues():
        try:
            f = open(os.path.join(datadir,file), "r")
            linenumber = 0
            for line in f.readlines():
                m = pattern.search(line)
                # we don't want to process every line, so remove html
                # from only those lines that match our search
                if m:
                    line = removeHtmlTags(line)
                    # match again since the line has changed
                    line = line.strip()
                    m = pattern.search(line)
                    if not m:
                        continue
                    if not matchedfiles.has_key(file):
                        matchedfiles[file] = list()

                    # even the line out with ..starting match ending...
                    linelength = 100
                    startline = line[:m.start()]
                    middleline = line[m.start():m.end()]
                    endline = line[m.end():].rstrip()
                    tokenlegth = (linelength - len(middleline))/2
                    el = 0
                    sl = tokenlegth - len(startline)
                    if sl <= 0:
                        sl = tokenlegth
                        el = tokenlegth
                    else: # sl > 0
                        el = tokenlegth + (tokenlegth - sl)
                    if sl == tokenlegth and len(startline) > 0:
                        startline = "...%s" % startline[-sl:]
                    if len(endline) > el:
                        endline = "%s..." % endline[:el]

                    matchedfiles[file].append("%04d: %s<div id=\"hit\">%s</div>%s\n" %(
                            linenumber,
                            startline,
                            middleline,
                            endline))
                linenumber += 1
            f.close()
        except:
            pass

    for file in matchedfiles.iterkeys():
        pline = ""

        for line in matchedfiles[file]:
            pline += line
        renderEntryLinks(list(ent.getOne(file)), pline)

    if len(matchedfiles) == 0: # no matches
        print l_search2

    print "</div>" # content3
    renderHtmlFooter()
    return

def renderDeleteComments(entry, commentnum):
    renderHtmlHeader("comments")
    print "<div id=\"content3\">"
    comments = entry.comments

    if len(comments) < commentnum:
        print "<p>No comment</p>"
        print "</body></html>"
        return
    comment = comments[commentnum-1]
    print "<ol>"
    print "<li>"
    print "<cite>%s</cite>:" % comment.getAuthorLink()

    print "<br />"
    print "<small>%s</small>" % (
        strftime(dateformat, comment.date.timetuple()))
    print "<p>%s</p>" % comment.getText()
    print "</li>"
    print "</ol>"

    print "<p>%s</p>" % l_do_you_delete
    print "<form action=\"%s/%s/?deletecomment\" method=\"post\" id=\"deleteform\">" % (baseurl,
                                                                                         quote_plus(entry.fileName[:-4]))
    print "<input type=\"hidden\" name=\"commentnum\" id=\"commentnum\" value=\"%s\"/>" % (commentnum)
    print "<input type=\"hidden\" name=\"name\" id=\"name\" value=\"%s\"/>" % entry.fileName[:-4]
    print "<p><input type=\"password\" name=\"password\" id=\"password\" size=\"22\" tabindex=\"1\" />"
    print "<label for=\"password\"><small>%s</small></label></p>" % l_passwd
    print "<p><input name=\"submit\" type=\"submit\" id=\"submit\" tabindex=\"5\" value=\"Submit\" />"
    print "</p></form>"
    print "</div>" # content3
    renderHtmlFooter()
    return

def renderHtml(entries, path, catelist, arclist, admin, page):
    """Render the blog. Some template stuff might be nice :D"""
    category = False
    if len(path) >= 1 and path[0] in catelist.keys():
        category = True

    # title
    title = None
    summary = False
    if len(entries) == 1:
        title = entries[0].headline
    elif category:
        title = path[0]

    if len(entries) > 1:
        summary = entrysummary

    rss = list()

    # additional rss feeds
    if category:
        rss.append("<link rel=\"alternate\" type=\"application/rss+xml\" title=\"%s: %s RSS Feed\" href=\"%s/%s/feed/\" />" % (blogname,path[0],baseurl,quote_plus(path[0])))
    elif len(entries) == 1:
        for cat in entries[0].cat:
            rss.append("<link rel=\"alternate\" type=\"application/rss+xml\" title=\"%s: %s RSS Feed\" href=\"%s/%s/feed/\" />" % (blogname,cat,baseurl,quote_plus(cat)))

    renderHtmlHeader(title, rss)

    print "<div id=\"content2\">"
    for entry in entries:
        print "<h2><a href=\"%s\">%s</a></h2>" % (
            entry.url,
            entry.headline)
        print "<div class=\"post\">"
        for line in entry.getText(summary):
            print line,
        print "</div>"

        if len(entries) > 1 and maxcomments > -1:
            nc = len(entry.comments)
            if nc > 0:
                print "<div class=\"comlink\">%s <a href=\"%s#comments\">%s</a></div>" % (
                    nc,
                    entry.url,
                    l_comments2)
            else:
                print "<div class=\"comlink\"><a href=\"%s#leave_acomment\">%s</a></div>" % (
                    entry.url,
                    l_no_comments)
        print "<div class=\"categories\">%s:" % l_categories
        num = 0
        for cat in entry.cat:
            num=num+1
            comma = ''
            if len(entry.cat) > num:
                comma = ', '
            print "<a href=\"%s/%s\">%s</a>%s" % (baseurl, quote_plus(cat), cat, comma)
        print "</div>"
        print "<div class=\"date\">%s: %s</div>" % (l_date, strftime(dateformat, entry.date.timetuple()))

        # comments
        if len(entries) == 1:
            numofcomment = 0
            if len(entry.comments) > 0 and maxcomments > -1:
                print "<h3><a name=\"comments\"></a>%s</h3>" % l_comments
                print "<ol style=\"list-style-type:none;\">"
                for comment in entry.comments:
                    numofcomment = numofcomment +1
                    print "<li>"
                    if gravatarsupport:
                        print "<img style=\"padding-right:5px;\""
                        print "src=\"http://gravatar.com/avatar/%s?s=40&d=identicon\" align=\"left\"/>" % (
                            comment.getEmailMd5Sum())
                    print "<cite>%s</cite>:" % comment.getAuthorLink()
                    print "<br />"
                    delcom = ""
                    if admin:
                        delcom = "<a href=\"%s/%s/?delcomment=%s\">(%s)</a>" % (baseurl,
                                                                                quote_plus(entry.fileName[:-4]),
                                                                                numofcomment,
                                                                                l_delete_comment)
                    print "<small><a name =\"comment-%s\" href=\"#comment-%s\">%s</a> %s </small>" % (
                        numofcomment,
                        numofcomment,
                        strftime(dateformat, comment.date.timetuple()),
                        delcom)
                    print "<p>%s</p>" % comment.getText()
                    print "</li>"
                print "</ol>"
            if maxcomments == -1 or len(entry.comments) >= maxcomments:
                print "<h3>%s</h3>" % l_no_comments_allowed
            else:
                print "<h3><a name=\"leave_acomment\"></a>%s</h3>" % l_leave_reply
                print "<form action=\"%s/%s/?postcomment\" method=\"post\"" % (
                    baseurl,
                    entry.fileName[:-4])
                print "id=\"commentform\" onsubmit=\"return validate_form(this)\">" # form
                print "<input type=\"hidden\" name=\"name\" id=\"name\" value=\"%s\"/>" % entry.fileName[:-4]
                print "<input type=\"hidden\" name=\"headline\" id=\"headline\" value=\"%s\"/>" % entry.headline
                print "<input type=\"hidden\" name=\"commentnum\" id=\"commentnum\" value=\"%s\"/>" % (numofcomment+1)
                print "<p><input type=\"text\" name=\"author\" id=\"author\" size=\"22\" tabindex=\"1\" />"
                print "<label for=\"author\"><small>%s</small></label></p>" % l_name_needed
                print "<p><input type=\"text\" name=\"email\" id=\"email\" size=\"22\" tabindex=\"2\" />"
                print "<label for=\"email\"><small>%s</small></label></p>" % l_email_needed
                print "<p><input type=\"text\" name=\"url\" id=\"url\" size=\"22\" tabindex=\"3\" />"
                print "<label for=\"url\"><small>%s</small></label></p>" % l_webpage
                print "<p><input type=\"text\" name=\"nospam\" id=\"nospam\" size=\"22\" tabindex=\"4\" />"
                print "<label for=\"nospam\"><small>%s</small></label></p>" % l_nospam_question
                print "<p>%s</p>" % l_no_html
                print "<p><textarea name=\"comment\" id=\"comment\" cols=\"40\" rows=\"7\" tabindex=\"4\"></textarea></p>"
                print "<p><input name=\"submit\" type=\"submit\" id=\"submit\" tabindex=\"5\" value=\"Submit\" />"
                print "<input type=\"hidden\" name=\"comment_post_ID\" value=\"11\" />"
                print "</p>"
                print "<p><input type=\"checkbox\" name=\"subscribe\" id=\"subscribe\" tabindex=\"6\" value=\"subscribe\">%s</label></p>" % l_notify_comments
                print "</form>"

    if len(entries) > 1:
        print "<div class=\"navi\">"
        if page > 0:
            print "<a href=\"%s/%s?page=%s\">%s</a>" % (
                baseurl,
                '/'.join(path),
                page-1,
                l_previouspage
                )
        if len(entries) == numberofentriesperpage:
            print "<a href=\"%s/%s?page=%s\">%s</a>" % (
                baseurl,
                '/'.join(path),
                page+1,
                l_nextpage
                )
        print "</div>"
    print "</div>" # content2

    # sidebar
    print "<div id=\"sidebar\">"
    sortedcat = catelist.keys()
    try:
        sortedcat.sort(key=locale.strxfrm)
    except: # python < 2.4 fails
        sortedcat.sort()
    print "<h2><a href=\"%s/categories\">%s</a></h2>" % (baseurl, l_categories)
    print "<ul>"
    for cat in sortedcat:
        print "<li><a href=\"%s/%s\">%s</a> (%s)</li>" % (
            baseurl, quote_plus(cat), cat, len(catelist[cat]))
    print "</ul>"

    # search
    print "<h2>%s</h2>" % l_search
    print "<form action=\"%s\" method=\"get\" id=\"searchform\">" % baseurl
    print "<input type=\"text\" name=\"search\" id=\"search\" size=\"15\" /><br />"
    print "<input type=\"submit\" value=\"%s\" />" % l_search
    print "</form>"

    if sidebarcomments:
        print "<h2>%s</h2>" % l_recent_comments
        comlist = getCommentList()
        if len(comlist) == 0:
            "No comments"
        else:
            print "<ul>"
            for com in comlist:
                print "<li>%s on <a href=\"%s/%s#comment-%d\">%s</a>"\
                    % (com["authorlink"], baseurl,
                       quote_plus(com["file"][:-4]), com["num"], com["subject"])
                print "</li>"
        print "</ul>"

    # archive
    print "<h2><a href=\"%s/archive\">%s</a></h2>" % (baseurl, l_archives)
    print "<ul>"
    sortedarc = arclist.keys()
    sortedarc.sort()
    sortedarc.reverse()
    for dat in sortedarc:
        print "<li><a href=\"%s/%s\">%s</a> (%s)</li>" % (
            baseurl, dat, dat, len(arclist[dat]))
    print "</ul>"

    if len(entries) == 1:
        print "<h2>%s</h2>" % l_admin
        print "<ul>"
        print "<li><a href=\"%s/%s/?admin\" rel=\"nofollow\">%s</a>" % (baseurl,
                                                                        quote_plus(entry.fileName[:-4]),
                                                                        l_admin_comments)
        print "</ul>"

    print "</div>" # sidebar

    renderHtmlFooter()

def renderFeed(entries, path, categorieslist):
    rfc822time = "%a, %d %b %Y %H:%M:%S +0200"
    print "Content-Type: text/xml; charset=%s\n" % encoding
    print "<?xml version=\"1.0\" encoding=\"%s\"?>" % encoding
    print "<!-- generator=\"Kukkaisvoima version %s\" -->" % version
    print "<rss version=\"2.0\""
    print "xmlns:content=\"http://purl.org/rss/1.0/modules/content/\""
    print "xmlns:wfw=\"http://wellformedweb.org/CommentAPI/\""
    print "xmlns:dc=\"http://purl.org/dc/elements/1.1/\""
    print ">"
    print "<channel>"
    if len(path) >= 1 and path[0] in categorieslist.keys():
        print "<title>%s: %s</title>" % (blogname, path[0])
    else:
        print "<title>%s</title>" % blogname
    print "<link>%s</link>" % baseurl
    print "<description>%s</description>" % description
    print "<pubDate>%s</pubDate>" % strftime(rfc822time, entries[0].date.timetuple())
    print "<lastBuildDate>%s</lastBuildDate>" % strftime(rfc822time, entries[0].date.timetuple())
    print "<generator>http://23.fi/kukkaisvoima/</generator>"
    print "<language>%s</language>" % language

    # print entries
    for entry in entries:
        print "<item>"
        print "<title>%s</title>" % entry.headline
        print "<link>%s</link>" % entry.url
        print "<comments>%s#comments</comments>" % entry.url
        print "<pubDate>%s</pubDate>" % strftime(rfc822time, entry.date.timetuple())
        print "<dc:creator>%s</dc:creator>" % entry.author
        for cat in entry.cat:
            print "<category>%s</category>" % cat
        print "<guid isPermaLink=\"false\">%s/</guid>" % entry.url
        print "<description><![CDATA[ %s [...]]]></description>" % entry.text[0]
        print "<content:encoded><![CDATA["
        for line in entry.text:
            print line,
        print "]]></content:encoded>"
        print "<wfw:commentRss>%s/feed/</wfw:commentRss>" % entry.url
        print "</item>"
    print "</channel>"
    print "</rss>"

# main program starts here
def main():
    path = ['']
    if os.environ.has_key('PATH_INFO'):
        path = os.environ['PATH_INFO'].split('/')[1:]
        path = [p for p in path if p != '']
    page = 0
    admin = False
    delcomment = 0
    postcomment = False
    deletecomment = False
    search = False
    searchstring = ""
    unsubscribe = False
    unsubscribe_id = ""

    if os.environ.has_key('QUERY_STRING'):
        querystr = os.environ['QUERY_STRING'].split('=')
        if len(querystr) == 2 and querystr[0] == 'page':
            try:
                page = int(querystr[1])
            except:
                page = 0
        elif querystr[0] == 'admin':
            admin = True
        elif querystr[0] == 'postcomment':
            postcomment = True
        elif querystr[0] == 'deletecomment':
            deletecomment = True
        elif len(querystr) == 2 and querystr[0] == 'delcomment':
            try:
                delcomment = int(querystr[1])
            except:
                delcomment = 0
        elif len(querystr) == 2 and querystr[0] == 'search':
            search = True
            searchstring = querystr[1]
        elif len(querystr) == 2 and querystr[0] == 'unsubscribe':
            unsubscribe = True
            unsubscribe_id = querystr[1]

    files = os.listdir(datadir)
    # read and validate the txt files
    entries = list()
    for entry in files:
        if not entry.endswith(".txt"):
            continue
        if not len(entry.split(":")) == 3:
            continue
        try:
            year, month, day = entry.split(":")[1].split("-")
            if int(year) == 0 or \
                    (int(month) < 1 or int(month) > 12) or \
                    (int(day) < 1 or int(day) > 31):
                continue
        except:
            continue
        entries.append(entry)

    filelist = {}
    for file in entries:
        filelist[generateDate(os.path.join(datadir,file))] = file

    # Read the main index
    indexold = list()
    try:
        indexoldfile = open(os.path.join(indexdir,'main.index'), 'rb')
        indexoldd = pickle.load(indexoldfile)
        indexoldfile.close()
        indexold = indexoldd.values()
    except:
        pass

    # generate categorieslist and archivelist
    categorieslist = {}
    archivelist = {}
    for file in filelist:
        name, date, categories = filelist[file][:-4].split(':')
        adate = date[:7]
        if adate.endswith('-'):
            adate =  "%s-0%s" % (adate[:4], adate[5])
        date = file
        categories = categories.split(',')
        for cat in categories:
            if categorieslist.has_key(cat):
                categorieslist[cat][date] = filelist[file]
            else:
                categorieslist[cat] = {}
                categorieslist[cat][date] = filelist[file]
        if archivelist.has_key(adate):
            archivelist[adate][date] = filelist[file]
        else:
            archivelist[adate] = {}
            archivelist[adate][date] = filelist[file]

    # Compare the index
    newarticles = Set(entries)^Set(indexold)
    if len(newarticles) > 0:
        # Pickle the categories
        for cat in categorieslist.keys():
            oldcategorieslist = None
            try:
                oldcatindex = open(os.path.join(indexdir,'%s.index' %cat), 'rb')
                oldcategorieslist = pickle.load(oldcatindex)
                oldcatindex.close()
            except:
                pass # :P
            # No old index or new articles in category, update the index
            if not oldcategorieslist or \
                    (oldcategorieslist and \
                         len(Set(oldcategorieslist.values())\
                                 ^Set(categorieslist[cat].values())) > 0):
                catindex = open(os.path.join(indexdir,'%s.index' %cat), 'wb')
                pickle.dump(categorieslist[cat], catindex)
                catindex.close()

        # Pickle the date archives
        for arc in archivelist.keys():
            oldarchivelist = None
            try:
                oldarcindex = open(os.path.join(indexdir,'%s.index' %arc), 'rb')
                oldarchivelist = pickle.load(oldarcindex)
                oldarcindex.close()
            except:
                pass # :P
            if not oldarchivelist or \
                    (oldarchivelist and \
                         len(Set(oldarchivelist.values())\
                                 ^Set(archivelist[arc].values())) > 0):
                arcindex = open(os.path.join(indexdir,'%s.index' %arc), 'wb')
                pickle.dump(archivelist[arc], arcindex)
                arcindex.close()
        # Pickle the main index
        index = open(os.path.join(indexdir,'main.index'), 'wb')
        pickle.dump(filelist, index)
        index.close()

    feed = False
    if len(path) > 0 and path[len(path)-1] == 'feed':
        feed = True
        numberofentriesperpage = 10 # feed always has 10
        page = 0

    ent = Entries(indexdir)

    if len(path) == 1 and path[0] == "archive":
        return renderArchive(ent)
    if len(path) >= 1 and path[0] == "categories":
        return renderCategories(categorieslist, ent, path)
    elif len(path) == 1 and search == True and searchstring != "":
        return renderSearch(filelist, ent, unquote_plus(searchstring))
    elif len(path) >= 1 and path[0] in categorieslist.keys():
        try:
            entries = ent.getMany(page, path[0])
        except:
            entries = ent.getMany(page)
    elif len(path) == 1 and path[0] in archivelist.keys():
        try:
            entries = ent.getMany(page, path[0])
        except:
            entries = ent.getMany(page)
    elif len(path) == 1 and postcomment:
        try:
            redirect = handleIncomingComment(cgi.FieldStorage(keep_blank_values=1))
            if redirect:
                print redirect
                return
            else:
                entries = ent.getOne("%s.txt" % unquote_plus(path[0]))
        except:
            entries = ent.getMany(page)
    elif len(path) == 1 and deletecomment:
        # check if this is incoming comment
        fs = cgi.FieldStorage(keep_blank_values=1)
        commentnum = int(fs.getvalue('commentnum'))
        password = fs.getvalue('password')
        name = fs.getvalue('name')
        filename = "%s.txt" % name
        if commentnum and name and password == passwd and passwd != 'password':
            deleteComment(filename, commentnum)
        print 'Location: %s/%s\n' % (baseurl, name)
    elif len(path) == 1 and unsubscribe and unsubscribe_id:
        name = unquote_plus(path[0])
        filename = "%s.txt" % name
        unsubscribeComments(filename, unsubscribe_id)
        print 'Location: %s/%s#comments\n' % (baseurl, name)
    elif len(path) == 1:
        try:
            entries = ent.getOne("%s.txt" % unquote_plus(path[0]))
        except:
            entries = ent.getMany(page)
    else:
        entries = ent.getMany(page)

    if delcomment > 0 and len(entries) == 1:
        renderDeleteComments(entries[0], delcomment)
    elif feed:
        renderFeed(entries, path, categorieslist)
    else:
        renderHtml(entries, path, categorieslist, archivelist, admin, page)
if __name__ == "__main__":
    main()
