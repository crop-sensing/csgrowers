<b> Quickstart Guide to CSGrowers App </b>

<i> Pre-requisites: </i>
- Box Drive mounted to file explorer
- Access to CSGrowers on Box Developer
- CSGrowers repository cloned to computer (please work out of the "testing" branch).
- Packages installed from requirements.txt (use pip install -r requirements.txt in your working directory).

<i> Instructions: </i>\
1.) Open desired Python file (Artois.py is currently running the most up-to-date version of code for the project).\
2.) On line 126 set the variable "path" to your shorterned username for your computer (f"C:/Users/{path}/...").\
3.) In the same directory as the Python files, place mapbox_info.json and box_info.json.

  - Audrey will send the mapbox_info.json and box_info.json file. 

4.) To run app successfully you need to generate a developer token from https://ucdavis.app.box.com/developers/console, hover over csgrowers, click the three dots and select "Generate Developer Token".
    
  - Alternative tutorial can be found here: https://developer.box.com/guides/authentication/tokens/developer-tokens/
  - Insert this token in box_info.json
  - NOTE: Box developer tokens expire every hour.

5.) To run app type: <b> python -m streamlit run main.py </b> in the terminal of your working directory. The app can be found at http://localhost:8501/Artois (each python script in the repostiory can be accessed by putting their title in the place of Artois).
