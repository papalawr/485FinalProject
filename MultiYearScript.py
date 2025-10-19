#script builds on basescript adapting it to accommodate for multiple years

import arcpy
arcpy.env.overwriteOutput = True
arcpy.env.workspace = r"C:\PSU\GEOG485\FinalProjectData\fire24_1.gdb"

#base feature class variable
firePerimeterFC = "firep24_1"
summaryTable = "fire_summary"

#records of interest variables
yearsOfInterest = [2025 ,2024 ,2023, 2022, 2021, 2020]

#fields of interest variables
yearField = 'YEAR_'
acresField = "GIS_ACRES"
startdateField = "ALARM_DATE"
enddateField = "CONT_DATE"

#counter variables
totalAcresBurntCounter = 0
totalBurnDaysCounter = 0
totalAcresBurntInYearCounter = 0
totalBurnDaysInYearCounter = 0

#new field variables for the fires in each year
firesPercentageOfAcreageBurnt = 'PercentOfTotalAcres'
firesPercentageofDaysBurnt= 'PercentOfTotalDays'
dataType = 'DOUBLE'

# Delete table if it already exists
if arcpy.Exists(summaryTable):
    arcpy.management.Delete(summaryTable)

# Create an empty table
arcpy.management.CreateTable(arcpy.env.workspace, summaryTable)

# Add fields
arcpy.management.AddFields(summaryTable, [
    ["Year", "LONG"],
    ["TotalAcres", "DOUBLE"],
    ["TotalDays", "DOUBLE"],
    ["PofAllAcres", "DOUBLE"],
    ["PofAllDays", "DOUBLE"]
])
print('created summary table and fields')

#get a total count of burnt acres and days on fire from master dataset
with arcpy.da.SearchCursor(firePerimeterFC, [acresField, startdateField, enddateField]) as totalCountsCursor:
    for totalCounts in totalCountsCursor:
        if totalCounts[0]:
            totalAcresBurntCounter += totalCounts[0]
        if totalCounts[1] and totalCounts[2]:
            totalBurnDaysCounter += (totalCounts[2]-totalCounts[1]).days

print(totalAcresBurntCounter)
print(totalBurnDaysCounter)

try:
    for year in yearsOfInterest:
        yearQuery = f"{yearField} = {year}"

        # SelectLayerByAttribute returns a layer object
        yearsLayer = arcpy.management.SelectLayerByAttribute(
            firePerimeterFC,
            "NEW_SELECTION",
            yearQuery
        )

        # Use that selection (layer object) when copying
        outputFC = f"fires_{year}"
        arcpy.management.CopyFeatures(yearsLayer, outputFC)

        print(f'created output fire features for {year}')


#use search cursor to select fields of interest within each fire feature class
        with arcpy.da.SearchCursor(outputFC, [acresField, startdateField, enddateField]) as yearTotals:
            for yearCounts in yearTotals:
                if yearCounts[0]:
                    totalAcresBurntInYearCounter += yearCounts[0]
                if yearCounts[1] and yearCounts[2]:
                    totalBurnDaysInYearCounter += (yearCounts[2] - yearCounts[1]).days

        print(f"{year} had {totalAcresBurntInYearCounter} acres burnt")
        print(f"{year} had {totalBurnDaysInYearCounter} burn days")


#add fields to each created feature class
        arcpy.management.AddFields(outputFC, [[firesPercentageOfAcreageBurnt, dataType], [firesPercentageofDaysBurnt, dataType]])

        print('added new fields to feature classes')

#populate new fields with an update cursor
        with arcpy.da.UpdateCursor(outputFC, (firesPercentageOfAcreageBurnt, acresField,
                                              firesPercentageofDaysBurnt, startdateField,
                                                enddateField)) as cursor:
            for row in cursor:
                row[0] = row[1] / totalAcresBurntInYearCounter * 100

                startDate = row[3]
                endDate = row[4]
                if startDate and endDate:
                    row[2] = ((endDate - startDate).days) / totalBurnDaysInYearCounter * 100

                cursor.updateRow(row)

        print('populated new fields in feature classes')

#update summary table field values
        pOfAllAcres = (totalAcresBurntInYearCounter / totalAcresBurntCounter) * 100 if totalAcresBurntCounter else 0
        pOfAllDays = (totalBurnDaysInYearCounter / totalBurnDaysCounter) * 100 if totalBurnDaysCounter else 0

# Insert a summary row into summary table
        with arcpy.da.InsertCursor(summaryTable,
                                   ["Year", "TotalAcres", "TotalDays", "PofAllAcres", "PofAllDays"]) as finalcursor:
            finalcursor.insertRow((year, totalAcresBurntInYearCounter, totalBurnDaysInYearCounter, pOfAllAcres, pOfAllDays))

    print('populated summary table')
except:
    print("failed to select fires from the given years")

finally:
    arcpy.management.Delete(yearsLayer)
    del totalCountsCursor, totalCounts
    del yearTotals, yearCounts
    del row, cursor
    del finalcursor