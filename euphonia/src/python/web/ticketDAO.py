import pymongo
import bson
from bson.objectid import ObjectId
from datetime import datetime, timedelta

class TicketDAO:

    def __init__(self, database):
        self.collection = database.queue

    def getTicketSummary(self, query, sortField, order=pymongo.ASCENDING, skip=0, limit=10):
        fquery = {}
        if query is not None:
            fquery = query
        results = self.collection.find(fquery, as_class=bson.son.SON).sort(sortField, order).skip(skip).limit(limit)
        ticketCount = results.count()
        tickets = []
        ticket = next(results, None)
        while ticket is not None:
            tickets.append(ticket)
            ticket = next(results, None)
        return {"tickets": tickets, "count": ticketCount}

    def approveTicket(self,ticket):
        print ticket
        self.collection.update({"iid":ObjectId(ticket)},{"$set": {"approved": True, "t": datetime.utcnow()}})

    def delayTicket(self,ticket,days):
        self.collection.update({"iid":ObjectId(ticket)},{"$set": {"approved": False, "t": datetime.utcnow()}})