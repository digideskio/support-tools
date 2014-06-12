#!/usr/bin/python
# -*- coding: latin-1 -*-

import codecs
import pymongo
import re
import pytz
from datetime import datetime, timedelta

WEEKS_BACK = 13
LIST_ROWS = 20

OFFICES = {
    'SYD': 'Australia/Sydney',
    'DUB': 'Europe/Dublin',
    'PA': 'US/Pacific',
    'NYC': 'US/Eastern',
    'ATX': 'US/Central',
    }

def GeneratorToString(func):
    def _func(*args, **kwargs):
        return ''.join(func(*args, **kwargs))
    return _func


class Date(object):
    _instance = None
    def __new__(c, *args, **kwargs):
        if not c._instance:
            c._instance = object.__new__(c, *args, **kwargs)
        return c._instance
    
    def __init__(self):
        self.end = datetime.combine(datetime.now().date(),
                                    datetime.min.time())
        #if FORCE_ENDDATE:
        #    self.end = FORCE_ENDDATE
        self.start = self.end - timedelta(weeks=WEEKS_BACK)
        self.asof = self.end - timedelta(days=1)
        self.weekago = self.end - timedelta(weeks=1)

    def WeeksBack(self, date):
        return (self.end - date).days / 7

    def GetOffset(self, office):
        tz = pytz.timezone(OFFICES[office])
        delta = tz.utcoffset(self.end)
        return (delta.seconds/3600 + delta.days*24)

    def GetEndDayOfWeek(self):
        t_struct = self.end.utctimetuple()
        return t_struct[6]

    def GetDayName(self, dow):
        return ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dow]
    

class Customer(object):
    def __init__(self, name):
        self.name = name
        self.tkt_by_priority = [0,0,0,0,0,0]

    def Name(self):
        return self.name

    def TrimmedName(self):
        maxlen = 20
        if len(self.name) > maxlen:
            return self.name[:maxlen-2] + '&hellip;'
        else:
            return self.name

    def JiraURL(self):
        return ('https://jira.mongodb.org/issues/'
                '?jql=reporter in membersOf("%s") '
                'ORDER BY created DESC') % self.Name()

    def AddTicket(self, ticket):
        pri = ticket.Priority()
        self.tkt_by_priority[pri] += 1

    def Heat(self):
        heat = 0
        weights = {1:10, 2:8, 3:4, 4:1, 5:1}  

        for pri in [1, 2, 3, 4, 5]:
            heat += self.tkt_by_priority[pri] * weights[pri]
        return heat

    def TicketCountsByPriority(self):
        pri = self.tkt_by_priority
        return [pri[1], pri[2], pri[3], pri[4]]


class Customers(object):
    def __init__(self):
        self.customers = {}
        pass

    def AddTicket(self, ticket):
        customer = ticket.Customer()
        if customer not in self.customers:
            self.customers[customer] = Customer(customer)
        self.customers[customer].AddTicket(ticket)

    def HeatTable(self):
        customers = self.customers.keys()
        customers.sort(key=lambda c: self.customers[c].Heat(),
                       reverse=True)

        def _row_gen():
            for cust in customers[:LIST_ROWS]:
                c = self.customers[cust]
                pris = []
                for cnt in c.TicketCountsByPriority():
                    if cnt:
                        pris.append(cnt)
                    else:
                        pris.append('&nbsp;')
                
                yield(["<a href='%s'>%s</a>" % (c.JiraURL(), c.TrimmedName())] +
                      pris)
        
        return _BasicTable('Customers With Hot Issues',
                           ['Customer', 'P1', 'P2', 'P3', 'P4'],
                           _row_gen,
                           'Tickets created, by combined weighted severity.',
                           align=['center', '','','','']
                           )

    def Customer(self, customer):
        if customer in self.customers:
            return self.customers[customer]
        else:
            return Customer(customer)

    
class Comment(object):
    re_mongo_email = re.compile(r'.+@(mongodb|10gen)\.com$')
    re_body_scrub = re.compile(r'\{(code|noformat)\}.+?\{\1\}', re.I | re.S)

    def __init__(self, json):
        self.json = json

    def Author(self):
        return self.json['author']['emailAddress']
    
    def isMongo(self):
        return bool(self.re_mongo_email.match(self.Author()))

    def isPublic(self):
        if 'visibility' in self.json:
          if self.json['visibility']['value'] == 'Developers':
              return False
        return True

    def DateTime(self):
        return self.json['updated']

    def Characters(self):
        body = self.json['body']
        body = self.re_body_scrub.sub('', body)
        return len(body)

    
class CommentList(object):
    def __init__(self, json):
        self.comments = []
        for js in json['comments']:
            self.comments.append(Comment(js))

    def FirstResponse(self):
        for c in self.comments:
            if c.isMongo() and c.isPublic():
                return c
        return None

    def FirstResponseTime(self):
        fr = self.FirstResponse()
        if fr:
            return fr.DateTime()
        else:
            return None

    def GenerateMongoComments(self):
        for c in self.comments:
            if c.isMongo():
                yield(c)

    def FirstCustomerComment(self):
        for c in self.comments:
            if not c.isMongo():
                return c

            
class Ticket(object):
    def __init__(self, json):
        self.json = json
        self.fields = self.json['fields']
        self.comments = CommentList(self.fields['comment'])

    def WeekCreated(self):
        return Date().WeeksBack(self.fields['created'])

    def WeekResolved(self):
        resdate = self.fields['resolutiondate']
        if not resdate:
            return None
        return Date().WeeksBack(resdate)

    def isResolved(self):
        return bool(self.fields['resolutiondate'])

    def TSECreateTime(self):
        if self.Project() == 'CS' and self.isProactive():
            cmt = self.comments.FirstCustomerComment()
            if cmt:
                return cmt.DateTime()
            else:
                return None
        else:
            return self.fields['created']

    def TSECreateWeek(self):
        return Date().WeeksBack(self.TSECreateTime())

    def Project(self):
        return self.fields['project']['key']

    def Number(self):
        return self.json['key']
    
    def Customer(self):
        cdict = self.fields.get('customfield_10030', {})
        if cdict:
            return cdict['name']
        else:
            return self.fields['reporter']['emailAddress']

    def Priority(self):
        return int(self.fields['priority']['id'])

    def IncomingWeight(self):
        return {1:10, 2:8, 3:4, 4:1, 5:1}[self.Priority()]

    def Components(self):
        c_list = self.fields.get('components', [])
        return [x['name'] for x in c_list]

    def URL(self):
        return 'http://jira.mongodb.org/browse/%s' % self.Number()

    def MongoCommentsForWeek(self, week):
        cnt = 0
        chars = 0
        weight = 0
        for c in self.comments.GenerateMongoComments():
            if week == Date().WeeksBack(c.DateTime()):
                cnt += 1
                chars += c.Characters()
                weight += c.Characters()**0.5
        return (cnt, chars, weight)

    def ResolutionHygiene(self):
        hygiene = set()
        if self.fields['issuelinks']: hygiene.add('Linked')
        if self.fields['components']: hygiene.add('Components')
        if self.fields['customfield_11050']: hygiene.add('Root Cause')
        return hygiene

    def TrimmedSummary(self):
        summary = self.fields['summary']
        if len(summary) > 40:
            return summary[:40] + '&hellip;'
        else:
            return summary

    def isProactive(self):
        return self.fields['issuetype']['name'] == 'Proactive'

    def isRespondedProactive(self):
        if self.isProactive():
            cmt = self.comments.FirstCustomerComment()
            return bool(cmt)
        return False

    def FirstCustomerResponseWeek(self):
        cmt = self.comments.FirstCustomerComment()
        if cmt:
            return Date().WeeksBack(cmt.DateTime())
        return None

    def isTSETicket(self):
        project = self.Project()
        if project in ['MMSSUPPORT', 'PARTNER', 'SUPPORT']:
            return True
        if project == 'CS':
            if self.isProactive():
                return self.isRespondedProactive()
            return True
        return False

class TimeSlot(object):
    def __init__(self, mode):
        self.mode = mode
        self.weeks = [0] * (WEEKS_BACK+1)

    def Add(self, week, value=1):
        if week < 0 or week > WEEKS_BACK:
            return
        self.weeks[week] += value

    def Get(self, week):
        return self.weeks[week]

    def ModeValue(self):
        if self.mode == 'current':
            return self.Get(0)
        elif self.mode == 'percentile':
            return self.Percentile()
        elif self.mode == 'average':
            return self.Average()
        return 0

    def Percentile(self, pct=0.95):
        v = self.weeks[:]
        v.sort()
    
        count = len(v)
        idx_target = (count-1) * pct
        idx_base = int(idx_target)
        pct_miss = pct - (idx_base+1) / float(count)
    
        p = (v[idx_base] +
             (v[idx_base+1] - v[idx_base]) * pct_miss/(1.0/count))
        return p

    def Average(self):
        return float(sum(self.weeks))/float(len(self.weeks))

    
class TimeMap(object):
    title = ""
    subtitle = ""
    
    def __init__(self, mode='current',
                 rgb_lo=(63,63,127), rgb_hi=(255,63,63),
                 ):
        self.mode = mode
        self.range = None
        self.rgb_lo = rgb_lo
        self.rgb_hi = rgb_hi

        self.slots = [[]] * 7
        for d in range(7):
            self.slots[d] = [TimeSlot(mode) for h in range(24)]

    def AddValue(self, time, value=1):
        week = Date().WeeksBack(time)
        t_struct = time.utctimetuple()
        hour = t_struct[3]
        dow = t_struct[6] # monday == 0
        self.slots[dow][hour].Add(week, value)
        self.range = None

    def GetColor(self, slot):
        value = slot.ModeValue()
        range = self.ModeValueRange()
        def _balance(pos):
            lo = self.rgb_lo[pos]
            hi = self.rgb_hi[pos]
            if range[1] == range[0]:
                mult = 0.5
            else:
                mult = float(hi-lo) / (range[1] - range[0])
            return int(lo + mult * (value - range[0]))
        color = '#%02x%02x%02x' % (
            _balance(0), _balance(1), _balance(2))
        return color
        
    def ModeValueRange(self):
        if not self.range:
            lo = float("inf")
            hi = float("-inf")
            for d in range(7):
                for h in range(24):
                    v = self.slots[d][h].ModeValue()
                    lo = min(lo, v)
                    hi = max(hi, v)
            
            self.range = (lo, hi)
        return self.range

    @GeneratorToString
    def HTMLTable(self):
        yield('<h2>%s</h2>' % self.title)
        if self.subtitle:
            yield('<span class=subtitle>%s</span>' % self.subtitle)
        yield('<table class=map>'
              '<tr class=header>'
              '<th>UTC')
        end_dow = Date().GetEndDayOfWeek()
        day_order = range(end_dow, 7) + range(0, end_dow)
        for dow in day_order:
            yield('<th>%s' % Date().GetDayName(dow))
        yield('</tr>')

        for hr in range(24):
            yield('<tr><th>%d:00' % hr)
            for dow in day_order:
                slot = self.slots[dow][hr]
                panel = (
                    '<span class=popup>'
                    'This Week: %d<br>'
                    'Last Week: %d<br>'
                    'Average: %0.1f<br>'
                    '95th Pctle: %0.1f'
                    '</span>' % (
                        slot.Get(0),
                        slot.Get(1),
                        slot.Average(),
                        slot.Percentile(),
                        )
                    )
                
                yield('<td class=hover style="background-color:%s">%d%s' %
                        (self.GetColor(slot), slot.Get(0), panel))
            yield('</tr>')
        yield('</table>')

    def TextTable(self):
        return ''

    
class CreatedMap(TimeMap):
    title = "Tickets Created by Hour"
    def AddTicket(self, ticket):
        if ticket.isTSETicket():
            self.AddValue(ticket.TSECreateTime())

    
class WeeklyStat(object):
    def __init__(self, name):
        self.name = name
        self.by_week = {}

    def Add(self, week, value = 1):
        self.by_week[week] = self.by_week.get(week, 0) + value

    def Get(self, week):
        return self.by_week.get(week, 0)

    def HTMLRow(self, weeks_back):
        base = self.Get(0)
        row = [self.name, '%1.0f' % base]
        for wk in weeks_back:
            this = self.Get(wk)
            row.append('%1.0f <small>%+0.1f%%</small>' %
                  (this, Gain(base, this)))
        return row

    @GeneratorToString
    def TextRow(self, weeks_back):
        base = self.Get(0)
        yield('%-20s %8.0f' % (self.name, base))
        for wk in weeks_back:
            this = self.Get(wk)
            yield('  %6.0f [%+3.0f%%]' %
                  (this, Gain(base, this)))
        yield('\n')


class WeeklyStatGroup(object):
    title = None
    subtitle = None
    def __init__(self):
        self.by_row = {}
        self.row_order = []
        self.week_list = range(WEEKS_BACK + 1)
                
    def AddValue(self, row, week, value=1):
        if row not in self.by_row:
            self.by_row[row] = WeeklyStat(row)
            self.row_order.append(row)
        self.by_row[row].Add(week, value)

    def WeeksList(self):
        l = []
        for w in [1, 4, 13, 52]:
            if w < WEEKS_BACK:
                l.append(w)
        l.append(WEEKS_BACK)
        return l
        
        
    def HTMLTable(self):
        week_list = self.WeeksList()
        headers = ['','This Week']
        for w in week_list:
            headers.append('vs %swk Ago' % w)
    
        def _row_gen():
            for row_name in self.row_order:
                yield(self.by_row[row_name].HTMLRow(week_list))

        return _BasicTable(self.title, headers, _row_gen, self.subtitle)

    @GeneratorToString
    def TextTable(self):
        week_list = self.WeeksList()
        yield('%s\n%s\n' % (self.title, '=' * len(self.title)))
        yield('%20s %8s' % (' ', 'This Wk'))
        for wk in week_list:
            yield('  %13s' % ('vs %dwk Ago' % wk,))
        yield('\n')
        for row_name in self.row_order:
            yield(self.by_row[row_name].TextRow(week_list))
        yield('\n')

        
class ByProjectStats(WeeklyStatGroup):
    ProjectMapping = [
        ('CS', ['CS']),
        ('MMSSupport', ['MMSSUPPORT']),
        ('Partner', ['PARTNER']),
        ('Support', ['SUPPORT']),
        ('TS (Non-MMS)', ['CS', 'SUPPORT', 'PARTNER']),
        ('TS (Total)', ['CS', 'SUPPORT', 'PARTNER', 'MMSSUPPORT']),
        #('Help', ['HELP']),
        #('Free', ['FREE']),
        ]

    def GetProjects(self, ticket):
        project = ticket.Project()
        result = []
        for name, projects in self.ProjectMapping:
            if project in projects:
                result.append(name)
        return result
        
class TicketsCreated(ByProjectStats):
    title = 'Tickets Created'
    def AddTicket(self, ticket):
        if ticket.isTSETicket():
            projects = self.GetProjects(ticket)
            for p in projects:
                self.AddValue(p, ticket.TSECreateWeek())

class TicketsResolved(ByProjectStats):
    title = 'Tickets Resolved'
    def AddTicket(self, ticket):
        resweek = ticket.WeekResolved()
        if resweek is not None:
            projects = self.GetProjects(ticket)
            for p in projects:
                self.AddValue(p, resweek)

class TicketWorkload(ByProjectStats):
    def AddTicket(self, ticket):
        if ticket.isTSETicket():
            wk =  ticket.TSECreateWeek()
            self.AddValue('Total', wk)
            projects = self.GetProjects(ticket)
            for p in projects:
                self.AddValue('Proj_%s' % p, wk)
            for c in ticket.Components():
                self.AddValue('Comp_%s' % c, wk)

                
class TicketComments(WeeklyStatGroup):
    title = 'MongoDB Comment Load'
    subtitle = 'Number of comments generated by MongoDB employees'
    def AddTicket(self, ticket):
        for week in range(WEEKS_BACK+1):
            cnt, chars, weight = ticket.MongoCommentsForWeek(week)
            self.AddValue('Comments', week, cnt)
            self.AddValue('Characters', week, chars)
            self.AddValue('Blended', week, weight)


class TicketHygiene(WeeklyStatGroup):
    title = 'Ticket Resolution Hygiene'
    subtitle = 'Tickets closed in the week that various annotations'
    def AddTicket(self, ticket):
        resweek = ticket.WeekResolved()
        if resweek is not None:
            for h in ticket.ResolutionHygiene():
                self.AddValue(h, resweek)

                
class ProactiveTickets(WeeklyStatGroup):
    title = 'Proactive Tickets'
    def AddTicket(self, ticket):
        if ticket.isProactive():
            self.AddValue('Created', ticket.WeekCreated())
            self.AddValue('Resolved', ticket.WeekResolved())
            self.AddValue('First Reaction', ticket.FirstCustomerResponseWeek())


class StatBox(object):
    def __init__(self):
        self.customers = Customers()
        self.tables = {
            'created': TicketsCreated(),
            'resolved': TicketsResolved(),
            'comments': TicketComments(),
            'hygiene': TicketHygiene(),
            'proactive': ProactiveTickets(),
            'createdmap': CreatedMap(),
            }
        self.workload = TicketWorkload()
        self.most_active = []

    def Customers(self):
        return self.customers
        
    def AddToMostActive(self, ticket):
        weight = ticket.MongoCommentsForWeek(0)[2]
        self.most_active.append((weight, ticket))
        self.most_active.sort(reverse=True)
        self.most_active = self.most_active[:LIST_ROWS]
        
    def ScanTicket(self, ticket):
        for table in self.tables.itervalues():
            table.AddTicket(ticket)

        if ticket.WeekCreated() == 0:
            self.customers.AddTicket(ticket)
        
        self.AddToMostActive(ticket)
        self.workload.AddTicket(ticket)

    def HTMLTables(self):
        d = {
            'table.custheat': self.customers.HeatTable(),
            'table.mostactive': self.ActiveTicketTable(),
            }
        
        for name, obj in self.tables.iteritems():
            d['table.%s' % name] = obj.HTMLTable()
        return d

    def TextTables(self):
        d = {}
        for name, obj in self.tables.iteritems():
            d['table.%s' % name] = obj.TextTable()
        return d

    def ActiveTicketTable(self):
        def _row_gen():
            for wgt, tkt in self.most_active:
                cmts, chars, wght = tkt.MongoCommentsForWeek(0)
                yield(["<a href='%s'>%s</a>" % (tkt.URL(), tkt.Number()),
                       tkt.Customer(), tkt.TrimmedSummary(),
                       cmts, chars, int(wght)])
        return _BasicTable('Most Active Tickets',
                           ['Ticket#', 'Customer', 'Summary',
                            'Cmts', 'Chars', 'Blended'],
                           _row_gen,
                           'Tickets with the most MongoDB comment traffic this week.',
                           align=['center', 'left', 'left', '', '', ''])

    
@GeneratorToString
def _BasicTable(title, headers, row_generator,
                subtitle=None, align=None):
    def _halign(i):
        if align and len(align) > i and align[i]:
            return u' style="text-align:%s"' % align[i]
        else:
            return u' style="text-align:right"'
    
    yield('<h2>%s</h2>' % title)
    if subtitle:
        yield('<span class=subtitle>%s</span>' % subtitle)
    yield('<table class=data>'
          '<tr class=header>')
    for h in headers:
        yield('<th>%s' % h)
    yield('</tr>')
    for row in row_generator():
        yield('<tr><th%s>%s' % (_halign(0), row[0]))
       
        for i, field in enumerate(row[1:]):
            yield(u'<td%s>%s' % (_halign(i+1), unicode(field)))
        yield('</tr>')
    yield('</table>')
        
    
def Gain(a, b):
    if not a:
       if b:
           return -100.0
       else:
           return 0.0
    if not b:
       return 100.0
    return((float(a)/b -1.0) * 100.0)

class TextReport(object):
    def __init__(self, statbox):
        self.stat_box = statbox

    @GeneratorToString
    def Text(self):
        yield('Weekly Metrics for Week Ending %s\n' %
              Date().asof.strftime('%Y-%m-%d'))

        tables = self.stat_box.TextTables()
        for name in [
                'table.created',
                'table.resolved',
                'table.proactive',
                'table.comments',
                'table.hygiene',
                ]:
            yield(tables[name])

    def SaveText(self):
        filename = 'WeeklyStats.%s.txt' % Date().end.strftime('%Y-%m-%d')
        f = codecs.open(filename, mode='w', encoding='utf-8')
        f.write(self.Text())
        f.close()

def DumpWorkload(stats):
    filename = 'Workload.%s.txt' % Date().end.strftime('%Y-%m-%d')
    f = codecs.open(filename, mode='w', encoding='utf-8')
    wl = stats.workload
    fields = sorted(wl.row_order, reverse=True)
    enddate = Date().asof

    f.write('\t'.join(['WkEnding'] + fields) + '\n')
    for wk in range(-1, WEEKS_BACK):
        date = enddate - timedelta(weeks=wk)
        datestr = date.strftime('%Y-%m-%d')
        row = [datestr]
        for fld in fields:
            val = wl.by_row[fld].Get(wk)
            row.append(val)
        f.write('\t'.join([str(x) for x in row]) + '\n')
    f.close()

    
class HTMLReport(object):
    def __init__(self, statbox):
        self.stat_box = statbox
        self.codeblocks = {
            'throughdate': Date().asof.strftime('%Y-%m-%d'),
            }

    def FetchData(self):
        self.GetTables()
        self.GetNovelCustomers()
                
    def GetTables(self):
        self.cust_db = self.stat_box.Customers()
        self.codeblocks.update(self.stat_box.HTMLTables())

    def GetNovelCustomers(self):
        weekback = Date().weekago
                
        conn = pymongo.MongoClient('localhost:27017')
        jira = conn.jira
       
        agg = jira.issues.aggregate([
           {'$match': {'fields.project.key': 'CS'}},
           {'$group': {'_id': '$fields.customfield_10030.name',
                       'start': {'$min': '$fields.created'}}},
           {'$match': {'start': {'$gte': Date().weekago, '$lte': Date().end }}},
           {'$sort': {'_id': 1}}
           ])

        linklist = []
        for row in agg['result']:
            c = self.cust_db.Customer(row['_id'])
            linklist.append("<a href='%s'>%s</a>" % (c.JiraURL(), c.Name()))

        html = """
        <h2>Novel Customers (%d)</h2>
        <span class=subtitle>Customers who used Commercial Support
            for the first time last week</span>
        <br> %s""" % (len(linklist), ',&ensp; '.join(linklist))
        self.codeblocks['list.novel'] = html

    def SaveHTML(self):
        filename = 'WeeklyStats.%s.html' % Date().end.strftime('%Y-%m-%d')
        f = codecs.open(filename, mode='w', encoding='utf-8')
        f.write(self.HTML())
        f.close()

    def HTML(self):
        return """
<head>
<title>Weekly Support Metrics %(throughdate)s</title>
<base target="_blank">
<style>
a {
    white-space: nowrap;
    }
h1 {
    font-size: 18pt;
    font-weight: bold;
    padding-top: 0pt;
    padding-bottom: 0pt;
    margin-bottom: 2pt;
    margin-top: 0pt;
    text-align: center;
    }
.subheading {
    text-align: center;
    }
.subtitle {
    font-size: 10pt;
    }
h2 {
    font-size: 14pt;
    font-weight:bold;
    padding-top: 6pt;
    padding-bottom: 0pt;
    margin-bottom: 2pt;
    }
td {
    vertical-align: top;
    }
.layout>tbody>tr>td {
    padding: 1em
    }
table.data, table.map {
   border-collapse:collapse
   }
.data, .data td, .data th, .map, .map th, .map td {
    border: 1px solid black;
    }
.data td, .map td {
    font-size: 12pt;
   }
.data th, .map th {
   font-weight: 600;
   font-size: 11pt;
   }
.header th {
    background-color: #0ff;
    text-align: center;
    }
.data tr:nth-child(odd) {
    background-color: #dff
    }
.map td {
    text-align: center;
    }
.popup {
    visibility: hidden;
    display: none;
    }
.hover:hover .popup {
    visibility: visible;
    float: right;
    display: block;
    position: absolute;
    border: 1px solid black;
    background-color: white
    }
</style>
</head>

<body>
<h1>Weekly Support Metrics</h1>
<p class=subheading>For the week ending %(throughdate)s UTC</span>
<hr>
 
<table class=layout>
  <tr>
    <td>%(table.created)s
    <td>%(table.resolved)s
  </tr>
  <tr>
    <td>%(table.proactive)s
    <td>%(table.hygiene)s
  </tr>
  <tr>
    <td>%(table.comments)s
  </tr>
</table>


<table class=layout>
  <tr>
    <td>%(table.custheat)s
    <td>%(table.mostactive)s
  </tr>
</table>
<table class=layout>
  <tr>
    <td>%(list.novel)s
  </tr>
</table>
%(table.createdmap)s
</body>
""" % self.codeblocks

    
def ScanRecentTickets():
    conn = pymongo.MongoClient('localhost:27017')
    jira = conn.jira

    cursor = jira.issues.find(
        {'fields.project.key': {'$in':
                                ['CS', 'SUPPORT', 'MMSSUPPORT', 'PARTNER']},
         '$or': [{'fields.created': {'$lte': Date().end, '$gte': Date().start}},
                 {'fields.updated': {'$lte': Date().end, '$gte': Date().start}}],
        })

    box = StatBox()
    for json in cursor:
        ticket = Ticket(json)
        box.ScanTicket(ticket)

    return box

    
def Main():
    statbox = ScanRecentTickets()
    html = HTMLReport(statbox)
    html.FetchData()
    html.SaveHTML()

    text = TextReport(statbox)
    text.SaveText()

    DumpWorkload(statbox)

Main()
 
