import pymongo
import bson
from bson.objectid import ObjectId
from datetime import datetime
import karakuriDAO

class TicketDAO:

    def __init__(self, karakuri):
        self.karakuri = karakuri

    def approveTicket(self,ticket):
        return self.karakuri.approveTicket(ticket)

    def delayTicket(self, ticket, days):
        return self.karakuri.sleepTicket(ticket, days*86400)