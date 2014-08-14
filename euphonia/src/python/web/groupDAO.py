class GroupDAO:

    def __init__(self,database):
        self.collection = database.mmsgroupreports


    def getGroupSummary(self,gid):
        results = self.collection.find({"GroupId":gid}).limit(2)
        groupDataPoint = next(results,None)
        dataPoints = []
        while groupDataPoint != None:
            dataPoints.append(groupDataPoint)
            groupDataPoint = next(results,None)
        return dataPoints