# g2-tl-info-extraction

This is an automation tool for extracting business infomation like business name, email, phone, address, etc.

Steps to run the code:
1. Create a folder named 'tmp' at the home directory(the same as /input and /output)
2. install the packages in the requirements.txt
3. upload a excel file(.xlsx) in the /input folder (for example input.xlsx), the file must contain a column named 'url' which has all the website urls
4. Change the SAVE_EVERY(if you want) in businfo_extract at line48 (default is 500), this indicates how many records you want to save at each batch
5. Run the script with command "python businfo_extract.py input.xlsx 10". 10 is a number you can define to let the script run beginning from the row10.
Or you can directly say "python businfo_extract.py input.xlsx" if you want to start from the first row
6. All temp files saved in /tmp will be removed after finishing the process
7. Output file will be saved in /output