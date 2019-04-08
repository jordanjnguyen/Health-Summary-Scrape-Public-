from bs4 import BeautifulSoup
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
import os, errno
import textwrap
import reportlab.platypus
import sys
from Tkinter import *
from datetime import date

# make reports and records directories
firstTime = False
try:
    os.makedirs('reports')
    reportsPath = os.getcwd()
    firstTime = True
except OSError as e:
    if e.errno != errno.EEXIST:
        raise
try:
    os.makedirs('records')
except OSError as e:
    if e.errno != errno.EEXIST:
        raise

# path
recordsPath = os.getcwd() + "/records/"
reportsPath = os.getcwd() + "/reports/"

# initialize sets
numRecords = 0
for f in os.listdir(recordsPath):
    if f.endswith('.XML'):
        numRecords += 1
if numRecords == 0:
    firstTime = True

searchSet = [set() for i in range(0, numRecords)]
recordNames = [None] * numRecords

# scrape medical records, store info, make pdf for each record
recordCount = 0
for f in os.listdir(recordsPath):
    if f.endswith('.XML'):
        print(f)
        print(recordCount)
        # summaryFile = open("DOC0002.XML", "r")
        summaryFile = open(os.path.join(recordsPath, f), "r")
        contents = summaryFile.read()
        soup = BeautifulSoup(contents, 'lxml')

        # isFHIR
        if soup.find("realmcode") is None:
            isFHIR = True
        else:
            isFHIR = False

        # Organization
        org = "n/a"
        if not isFHIR:
            org = soup.find("representedorganization")
            org = org.contents[1]
            org = org.text

        # name
        if isFHIR:
            given = soup.find('given').contents[0].text
        else:
            given = soup.find('given').text
        family = soup.find('family').text

        # address
        if isFHIR:
            street = soup.find('line').contents[0]
        else:
            street = soup.find('streetaddressline')
        city = soup.find('city')
        state = soup.find('state')
        zipcode = soup.find('postalcode')
        country = soup.find('country')
        addr = street.text + " " + city.text + ", " + state.text + " " + zipcode.text + " " + country.text

        # phone
        if isFHIR:
            phone = soup.find('telecom')
            phone = phone.contents[0].contents[2].text
        else:
            phone = soup.find("telecom", {"use":"MC"})["value"]
            phone = phone[4:]

        # race
        if isFHIR:
            race = soup.find("valuecoding").contents[2].text
        else:
            if soup.find("racecode").has_attr("displayname"):
                race = soup.find("racecode")["displayname"]
            elif soup.find("racecode").has_attr("nullflavor"):
                race = soup.find("racecode")["nullflavor"]
            else:
                race = ""

        # dead or alive
        isAlive = True

        if isFHIR:
            if soup.find("deceaseddatetime") != None:
                isAlive = False

                dDate = soup.find("deceaseddatetime").text
                dYear = int(dDate[:4])
                dMonth = int(dDate[5:7])
                dDay = int(dDate[8:10])
            else:
                dDate = "n/a"
                dYear = "n/a"
                dMonth = "n/a"
                dDay = "n/a"

        else:
            dDate = "n/a"
            dYear = "n/a"
            dMonth = "n/a"
            dDay = "n/a"

        # age and birthdate
        if isFHIR:
            bDate = soup.find("birthdate").text
            bYear = int(bDate[:4])
            bMonth = int(bDate[5:7])
            bDay = int(bDate[8:10])

            today = date.today()
            if isAlive:
                age = today.year - bYear - ((today.month, today.day) < (bMonth, bDay))
            else:
                age = dYear - bYear - ((dMonth, dDay) < (bMonth, bDay))
        else:
            bDate = soup.find("birthtime")["value"]
            bYear = int(bDate[:4])
            bMonth = int(bDate[4:6])
            bDay = int(bDate[6:])
            bDate = str(bYear) + "-" + str(bMonth) + "-" + str(bDay)

            today = date.today()
            if isAlive or not isFHIR:
                age = today.year - bYear - ((today.month, today.day) < (bMonth, bDay))
            else:
                age = dYear - bYear - ((dMonth, dDay) < (bMonth, bDay))

        # hospital
        def is_hospital(tag):
            next = tag.next_sibling
            if next is not None:
                if next.name == "resourcetype":
                    next2 = tag.next_sibling.next_sibling
                    if next2 is not None:
                        if next2.name == "contact":
                            return True
                return False

        if isFHIR:
            hospitalName = soup.find(is_hospital).text
        else:
            hospitalName = "n/a"

        # allergies
        if not isFHIR:
            def is_allergy(tag):
                if tag.has_attr("id"):
                    return "allergen" in tag.get("id")
            allergyList = soup.find_all(is_allergy)

            allergyStrings = ["" for x in range(len(allergyList))]
            i = 0
            for a in allergyList:
                allergyStrings[i] = a.get_text()
                i = i + 1

        # medication and dosage
        if isFHIR:
            medicationInfo = soup.find_all("medicationcodeableconcept")
            medicationStrings = ["" for x in range(len(medicationInfo))]
            i = 0
            for m in medicationInfo:
                medicationStrings[i] = medicationInfo[i].contents[1].contents[0].contents[2].text
                i += 1
        else:
            def is_medication(tag):
                if tag.has_attr("id"):
                    return "med" in tag.get("id")
            medicationList = soup.find_all(is_medication)

            medicationStrings = ["" for x in range(len(medicationList))]
            i = 0
            for medication in medicationList:
                medicationStrings[i] = medication.get_text()
                i = i + 1

        # med directions
        if not isFHIR:
            def is_direc(tag):
                if tag.has_attr("id"):

                    return "sig" in tag.get("id")
            direcList = soup.find_all(is_direc)

            direcStrings = ["" for x in range(len(direcList))]
            i = 0
            for direc in direcList:
                direcStrings[i] = direc.get_text()
                direcStrings[i] = '. '.join(i.capitalize() for i in direcStrings[i].split('. '))
                i = i + 1

        # med start date
        if isFHIR:
            medStart = soup.find_all("authoredon")
            medStartStrings = ["" for x in range(len(medStart))]
            i = 0
            for s in medStart:
                medStartStrings[i] = medStart[i].text
                medStartStrings[i] = medStartStrings[i][:10]
                i += 1
        else:
            def is_start(tag):
                if "Sutter" in org:
                    prev = tag.previous_sibling
                    if prev is None:
                        return False
                    if not hasattr(prev, "has_attr"):
                        return False
                    if prev.has_attr("id"):
                        return "med" in prev.get("id")
                else:
                    prev = tag.previous_sibling
                    if prev is None:
                        return False
                    prev = prev.previous_sibling
                    if prev is None:
                        return False
                    if not hasattr(prev, "has_attr"):
                        return False
                    if prev.has_attr("id"):
                        if "sig" in prev.get("id"):
                            return "sig" in prev.get("id")
                        elif "med" in prev.get("id"):
                            return "med" in prev.get("id")
                    return False
            startList = soup.find_all(is_start)

            medStartStrings = ["" for x in range(len(medicationList))]
            i = 0
            for start in startList:
                medStartStrings[i] = start.get_text()
                i = i + 1

        # med end date
        if not isFHIR:
            def is_end(tag):
                prev = tag.previous_sibling
                if prev is None:
                    return False
                prev = prev.previous_sibling
                if prev is None:
                    return False
                prev = prev.previous_sibling
                if prev is None:
                    return False
                if not hasattr(prev, "has_attr"):
                    return False
                if prev.has_attr("id"):
                    return "sig" in prev.get("id")
                return False
            endList = soup.find_all(is_end)

            endStrings = ["" for x in range(len(medicationList))]
            i = 0
            for end in endList:
                endStrings[i] = end.get_text()
                i = i + 1

        # med active status
        if isFHIR:
            active = soup.find_all("medicationcodeableconcept")
            i = 0
            activeStrings = ["" for x in range(len(active))]
            for a in active:
                #for r in range(7):
                while active[i].name != "status":
                    active[i] = active[i].previous_sibling
                activeStrings[i] = active[i].text.capitalize()
                i += 1
        else:
            def is_active(tag):
                prev = tag.previous_sibling
                if prev is None:
                    return False
                prev = prev.previous_sibling
                if prev is None:
                    return False
                prev = prev.previous_sibling
                if prev is None:
                    return False
                prev = prev.previous_sibling
                if prev is None:
                    return False
                if not hasattr(prev, "has_attr"):
                    return False
                return is_direc(prev)
            activeList = soup.find_all(is_active)

            activeStrings = ["" for x in range(len(medicationList))]
            i = 0
            for active in activeList:
                activeStrings[i] = active.get_text()
                i = i + 1

        # shots
        if isFHIR:
            shotInfo = soup.find_all("vaccinecode")
            shotStrings = ["" for x in range(len(shotInfo))]
            j = 0
            for i in shotInfo:
                shotStrings[j] = shotInfo[j].contents[0].text  # .contents[1].contents[3]
                j += 1
            shotdateInfo = soup.find_all("vaccinecode")
            shotdateStrings = ["" for x in range(len(shotdateInfo))]
            i = 0
            for a in shotdateInfo:
                shotdateStrings[i] = shotdateInfo[i].next_sibling.next_sibling.next_sibling.text
                i += 1
        else:
            def is_shot(tag):
                if tag.has_attr("id"):
                    return "immunization" in tag.get("id")
            shotList = soup.find_all(is_shot)

            shotStrings = ["" for x in range(len(shotList))]
            i = 0
            for s in shotList:
                shotStrings[i] = s.get_text()
                i = i + 1
            # Active Problems
            def is_problem(tag):
                if tag.has_attr("id"):
                    return "problem" in tag.get("id")
            probList = soup.find_all(is_problem)

            probStrings = ["" for x in range(len(probList))]
            i = 0
            for p in probList:
                probStrings[i] = p.get_text()
                i = i + 1

        # diseases
        if isFHIR:
            diseaseInfo = soup.find_all("asserteddate")
            diseaseStrings = ["" for x in range(len(diseaseInfo))]
            diseasedateStrings = ["" for x in range(len(diseaseInfo))]
            j = 0
            for i in diseaseInfo:
                diseaseStrings[j] = diseaseInfo[j].next_sibling.contents[0].text
                diseasedateStrings[j] = diseaseInfo[j].text[:10]
                j += 1

        # Placeholder values
        if isFHIR:
            allergyStrings = "" # ["" for x in range(len(medicationStrings))]
            direcStrings = ["" for x in range(len(medicationStrings))]
            # medStartStrings = ["" for x in range(len(medicationStrings))]
            endStrings = ["" for x in range(len(medicationStrings))]
            # activeStrings = ["" for x in range(len(medicationStrings))]
            probStrings = "" # ["" for x in range(len(medicationStrings))]

        # Add values to searchSet
        searchSet[recordCount].add(given.lower())
        searchSet[recordCount].add(family.lower())
        searchSet[recordCount].add(addr.lower())
        searchSet[recordCount].add(phone.lower())
        searchSet[recordCount].add(race.lower())
        searchSet[recordCount].add(bDate.lower())
        searchSet[recordCount].add(hospitalName.lower())

        i = 0
        for a in allergyStrings:
            searchSet[recordCount].add(allergyStrings[i].lower())
            i += 1
        i = 0
        for m in medicationStrings:
            searchSet[recordCount].add(medicationStrings[i].lower())
            i += 1
        i = 0
        for d in direcStrings:
            searchSet[recordCount].add(direcStrings[i].lower())
            i += 1
        i = 0
        for m in medStartStrings:
            searchSet[recordCount].add(medStartStrings[i].lower())
            i += 1
        i = 0
        for e in endStrings:
            searchSet[recordCount].add(endStrings[i].lower())
            i += 1
        i = 0
        for a in activeStrings:
            searchSet[recordCount].add(activeStrings[i].lower())
            i += 1
        i = 0
        for s in shotStrings:
            searchSet[recordCount].add(shotStrings[i].lower())
            i += 1
        i = 0
        for a in probStrings:
            searchSet[recordCount].add(probStrings[i].lower())
            i += 1


        # make PDF
        c = canvas.Canvas(reportsPath + str(recordCount) + "_" + given + "_report" +  ".pdf")
        recordNames[recordCount] = str(recordCount) + "_" + given + "_report" +  ".pdf"
        # c.setFillColorRGB(255,0,98)

        # Title
        c.setFont("Helvetica-Bold", 14)
        c.drawString(225, 820, "Patient Health Summary")

        # Page Number
        pageNum = 1
        c.setFont("Helvetica", 12)
        c.drawString(540, 20, "Page 1")

        xLeft = 30
        xIndent = xLeft + 20
        yStart = 790
        gap = 15
        g = 3
        # Patient Info: Name, addr, race, phone
        c.setFont("Helvetica-Bold", 12)
        c.drawString(xLeft, yStart, "Patient Info")
        c.setFont("Helvetica", 7)
        c.drawString(xIndent, yStart - gap, "Name: " + given + " " + family)
        addrString = "Address: " + addr
        aSpace = 0
        if len(addrString) > 70:
            wrap_text = textwrap.wrap(addrString, width = 70)
            c.drawString(xIndent, yStart - gap * 2, wrap_text[0])
            c.drawString(xIndent + 30, yStart - gap - 23, wrap_text[1])
            c.drawString(xIndent, yStart - gap * 3 - 6, "DOB: " + bDate + " (" + str(age) + " years old)")
            if(dDate != "n/a"):
                c.drawString(xIndent, yStart - gap * 4 - 6, "DOD: " + dDate)
            g += 2
        else:
            c.drawString(xIndent, yStart - gap * 2, "Address: " + addr)
            c.drawString(xIndent, yStart - gap * 3, "DOB: " + bDate + " (" + str(age) + " years old)")
            if(dDate != "n/a"):
                c.drawString(xIndent, yStart - gap * 4, "DOD: " + dDate)
                aSpace = 23
            else:
                aSpace = 11
        c.drawString(300, yStart - gap, "Race: " + race)
        c.drawString(300, yStart - gap * 2, "Phone #: " + phone)
        c.drawString(300, yStart - gap * 3, "Hospital: " + hospitalName)

        # Allergies
        c.setFont("Helvetica-Bold", 12)
        c.drawString(xLeft, (yStart - gap * g) - 15 - aSpace, "Allergies")
        yTemp = (yStart - gap * (g+1)) - 15 - aSpace

        c.setFont("Helvetica", 7)
        i = 0
        for a in allergyStrings:
            c.drawString(xIndent, yTemp, allergyStrings[i])
            i = i + 1
            yTemp = yTemp - gap
            if yTemp < 70:
                c.showPage()
                yTemp = 790
                pageNum = pageNum + 1
                c.setFont("Helvetica", 12)
                c.drawString(540, 20, "Page " + str(pageNum))
            c.setFont("Helvetica", 7)

        # Medication
        yTemp = yTemp - 10
        c.setFont("Helvetica-Bold", 12)
        c.drawString(xLeft, yTemp, "Medication")
        yTemp = yTemp - gap
        if len(medicationStrings) == 0:
            yTemp = yTemp - gap/2
        if yTemp < 70:
            c.showPage()
            yTemp = 790
            pageNum = pageNum + 1
            c.setFont("Helvetica", 12)
            c.drawString(540, 20, "Page " + str(pageNum))
        c.setFont("Helvetica-Bold", 12)

        i = 0

        gaptemp = 12
        for m in medicationStrings:
            c.setFont("Helvetica-Bold", 8)
            c.drawString(xIndent, yTemp, medicationStrings[i])
            c.setFont("Helvetica", 7)

            originalstring = "Directions: " + direcStrings[i]

            if len(originalstring) > 150:
                wrap_text = textwrap.wrap(originalstring, width = 150)
                c.drawString(xIndent + 20, yTemp - gap, wrap_text[0])
                if yTemp < 70:
                    c.showPage()
                    yTemp = 790
                    pageNum = pageNum + 1
                    c.setFont("Helvetica", 12)
                    c.drawString(540, 20, "Page " + str(pageNum))
                c.setFont("Helvetica", 7)
                c.drawString(xIndent + 20 + 36, yTemp - gap - 9, wrap_text[1])
                if yTemp < 70:
                    c.showPage()
                    yTemp = 790
                    pageNum = pageNum + 1
                    c.setFont("Helvetica", 12)
                    c.drawString(540, 20, "Page " + str(pageNum))
                c.setFont("Helvetica", 7)
                yTemp = yTemp - 8
                if yTemp < 70:
                    c.showPage()
                    yTemp = 790
                    pageNum = pageNum + 1
                    c.setFont("Helvetica", 12)
                    c.drawString(540, 20, "Page " + str(pageNum))
                c.setFont("Helvetica", 7)
            else:
                c.drawString(xIndent + 20, yTemp - gap, originalstring)
                yTemp = yTemp - 2
                if yTemp < 70:
                    c.showPage()
                    yTemp = 790
                    pageNum = pageNum + 1
                    c.setFont("Helvetica", 12)
                    c.drawString(540, 20, "Page " + str(pageNum))
                c.setFont("Helvetica", 7)

            c.drawString(xIndent + 20, yTemp - gaptemp * 2, "Status: " + activeStrings[i])
            if yTemp < 70:
                c.showPage()
                yTemp = 790
                pageNum = pageNum + 1
                c.setFont("Helvetica", 12)
                c.drawString(540, 20, "Page " + str(pageNum))
            c.setFont("Helvetica", 7)
            c.drawString(xIndent + 20, yTemp - gaptemp * 3, "Start Date: " + medStartStrings[i])
            if yTemp < 70:
                c.showPage()
                yTemp = 790
                pageNum = pageNum + 1
                c.setFont("Helvetica", 12)
                c.drawString(540, 20, "Page " + str(pageNum))
            c.setFont("Helvetica", 7)
            c.drawString(xIndent + 20, yTemp - gaptemp * 4, "End Date: " + endStrings[i])
            if yTemp < 70:
                c.showPage()
                yTemp = 790
                pageNum = pageNum + 1
                c.setFont("Helvetica", 12)
                c.drawString(540, 20, "Page " + str(pageNum))
            c.setFont("Helvetica", 7)
            i = i + 1
            yTemp = (yTemp - gaptemp * 5) - 10
            if yTemp < 70:
                c.showPage()
                yTemp = 790
                pageNum = pageNum + 1
                c.setFont("Helvetica", 12)
                c.drawString(540, 20, "Page " + str(pageNum))
            c.setFont("Helvetica", 7)

        # Shots
        c.setFont("Helvetica-Bold", 12)
        c.drawString(xLeft, yTemp, "Immunizations")
        yTemp = yTemp - gap
        if yTemp < 70:
            c.showPage()
            yTemp = 790
            pageNum = pageNum + 1
            c.setFont("Helvetica", 12)
            c.drawString(540, 20, "Page " + str(pageNum))
        c.setFont("Helvetica", 12)
        i = 0
        c.setFont("Helvetica", 7)
        if not isFHIR:
            for s in range(len(shotStrings)/2):
                c.drawString(xIndent, yTemp, shotStrings[i])
                i = i + 2
                yTemp = yTemp - gap
                if yTemp < 70:
                    c.showPage()
                    yTemp = 790
                    pageNum = pageNum + 1
                    c.setFont("Helvetica", 12)
                    c.drawString(540, 20, "Page " + str(pageNum))
                c.setFont("Helvetica", 7)
        else:
            for s in range(len(shotStrings)):
                c.drawString(xIndent, yTemp, shotStrings[i] + ":  " + shotdateStrings[i][:10])
                i += 1
                yTemp = yTemp - gap
                if yTemp < 70:
                    c.showPage()
                    yTemp = 790
                    pageNum = pageNum + 1
                    c.setFont("Helvetica", 12)
                    c.drawString(540, 20, "Page " + str(pageNum))
                c.setFont("Helvetica", 7)

        yTemp = yTemp - 10
        if yTemp < 70:
            c.showPage()
            yTemp = 790
            pageNum = pageNum + 1
            c.setFont("Helvetica", 12)
            c.drawString(540, 20, "Page " + str(pageNum))

        #Active Problems
        c.setFont("Helvetica-Bold", 12)
        c.drawString(xLeft, yTemp, "Active Problems")
        yTemp = yTemp - gap
        c.setFont("Helvetica", 7)
        i = 1
        for p in range(len(probStrings)/2):
            c.drawString(xIndent, yTemp, probStrings[i])
            yTemp = yTemp - gap
            i = i + 2
            if yTemp < 70:
                c.showPage()
                yTemp = 790
                pageNum = pageNum + 1
                c.setFont("Helvetica", 12)
                c.drawString(540, 20, "Page " + str(pageNum))
            c.setFont("Helvetica", 7)

        c.save()
        recordCount += 1

# check if there are records in the records directory
if firstTime:
    print("Please put medical records into the records directory")

# search
# http://code.activestate.com/recipes/578860-setting-up-a-listbox-filter-in-tkinterpython-27/
class Application(Frame):

    def __init__(self, master=None):
        Frame.__init__(self, master)

        self.pack()
        self.create_widgets()

    # Create main GUI window
    def create_widgets(self):
        self.search_var = StringVar()
        self.search_var.trace("w", lambda name, index, mode: self.update_list()).decode(sys.stdin.encoding)
        self.entry = Entry(self, textvariable=self.search_var, width=13)
        self.lbox = Listbox(self, width=45, height=15)

        self.entry.grid(row=0, column=0, padx=10, pady=3)
        self.lbox.grid(row=1, column=0, padx=10, pady=3)

        # Function for updating the list/doing the search.
        # It needs to be called here to populate the listbox.
        self.update_list()

    def update_list(self):
        search_term = self.search_var.get().lower().decode(sys.stdin.encoding)
        # Just a generic list to populate the listbox
        self.lbox.delete(0, END)

        found = False
        i = 0
        for item in recordNames:
            if search_term.lower() in searchSet[i]:
                found = True
                self.lbox.insert(END, item)
            if not found:
                for var in searchSet[i]:
                    if search_term in var:
                        self.lbox.insert(END, item)
                        break
            i += 1
            found = False

root = Tk()
root.title('Record Search')
app = Application(master=root)
# print 'Starting mainloop()'
app.mainloop()
