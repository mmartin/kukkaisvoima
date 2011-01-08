"""

This file is part fo Kukkaisvoima. Kukkaisvoima a lightweight weblog
system.

Copyright (C) 2006-2008 Petteri Klemola

This is config file. Kukkaisvoima's license don't affect this file.

You should keep this file private and see that this in not readable
from public web. For example when using Apache webserver create
.htaccess file with the following entry:

<files kukkaisvoima_settings.py>
 order allow,deny
 deny from all
</files>

"""

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
# Entry and comment Date format
dateformat = "%F %T"
# Sidebar Archive Date format
archivedateformat = "%Y-%m"

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
l_recent_comments_list = "%(author)s on %(post)s"
l_footer = "Powered by %(link)s version %(version)s"

