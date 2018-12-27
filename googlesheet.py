import pygsheets

gc = pygsheets.authorize(outh_file='credentials.txt')

def check(name,header=None):
	# if spreadsheet does not exist, creates it and writes headers
    ssheets = gc.list_ssheets()
    for ssheet in ssheets:
        if name in ssheet['name']:
            print(name,'exists')
            return
    else:
        spreadsheet = gc.create(name)
        worksheet = spreadsheet.sheet1
        worksheet.resize(rows=1, cols=len(header))
        worksheet.update_row(1, header)
        print('created',name)
    return

def append(name,valrow=None):
	# appends row to the end of worksheet
    spreadsheet = gc.open(name)
    worksheet = spreadsheet.sheet1
    worksheet.add_rows(1)
    num_rows = len(worksheet.get_all_values())
    worksheet.update_row(num_rows + 1, valrow)
