from bs4 import BeautifulSoup
import time
import os

#index of file data
print("-------------------------------")
main_index_msb = """<!DOCTYPE html>
<html lang="en" >
<head>
  <meta charset="UTF-8">
  <title>x3beche - dictionary</title>
  <link rel="icon" href="favicon.ico">
  <link href="https://fonts.googleapis.com/css?family=Lato" rel="stylesheet"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/meyer-reset/2.0/reset.min.css">
<link rel="stylesheet" href="./style.css">

</head>
<body>
<!-- partial:index.partial.html -->
<div class="container">
  <h2>X3beche  PDF  Dictionary <small></small></h2>
  <ul class="responsive-table">
    <li class="table-header"><div class="col col-1">ID</div><div class="col col-2">Document Name</div><div class="col col-3">Upload Date</div><div class="col col-4">File Size</div></li>\n"""
main_index_lsb = """  </ul>
</div>
<!-- partial -->
</body>
</html>
"""
contents = """"""
contents_new = """"""

#saving last document
with open("index.html", "r") as file:
    data = BeautifulSoup(file.read(), "html.parser")
    documents = data.find_all(class_="document")
for x in range(0,len(documents)):
    
    file_link       = documents[x]['href']
    name            = documents[x].find(class_="col col-2").text.strip().replace("\n","")
    date            = documents[x].find(class_="col col-3").text.strip().replace("\n","")
    file_size       = documents[x].find(class_="col col-4").text.strip().replace("\n","")
    
    contents += f'      <a class="document" href="{file_link}" target="_blank"><li class="table-row"><div class="col col-1" data-label="ID">{x+1}</div><div class="col col-2" data-label="Document Name"><strong>{name}</strong></div><div class="col col-3" data-label="Upload Date">{date}</div><div class="col col-4" data-label="File Size">{file_size}</div></li></a>\n'
    last_id = x+2

    print(f"|- {name}")

#getting new file's information
new_file_name = input('-------------------------------\nEnter "q" for exit\nEnter Document Title : ')
if new_file_name == "q": exit()
new_file_doc_name = input("Enter Document Name : ")
if new_file_doc_name == "q": exit()

#saving new file
try:
    file_size = str(round(os.path.getsize(f'documents\\{new_file_doc_name}')*0.000001, 2))+" MB"
    date = time.strftime('%x')+" | "+time.strftime('%X')
    contents_new = contents + f'      <a class="document" href="documents/{new_file_doc_name}" target="_blank"><li class="table-row"><div class="col col-1" data-label="ID">{last_id}</div><div class="col col-2" data-label="Document Name"><strong>{new_file_name}</strong></div><div class="col col-3" data-label="Upload Date">{date}</div><div class="col col-4" data-label="File Size">{file_size}</div></li></a>\n'

    try:
        with open("index.html", "w") as file:
            file.write(main_index_msb+contents_new+main_index_lsb)
            print("File added to list successfuly.")
    
    except:
        with open("index.html", "w") as file:
            file.write(main_index_msb+contents+main_index_lsb)
            print("There was an error detected while writing to the file, but no problem in main file.")
except:
    print("File didn't found on 'documents' folder.")
print("-------------------------------")