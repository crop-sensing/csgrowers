## CSGrowers README

### Data Sources and Methods

The non-user data you see on our app comes from three sources: CIMIS, OpenET, and the Crop Sensing Group, a subgroup of SAWS-ARS (Sustainable Agricultural Water Systems-Agricultural Research Service). Since this is a **near real-time tool** the sources of data have data quality caveats. I will now discuss how we collect, manipulate, and manage the data.

### CIMIS
CIMIS's reference evapotranspiration (ET) data is gathered via their [Spatial Report](https://cimis.water.ca.gov/SpatialData.aspx). We use the coordinates of the growers who have opted into our project to collect CIMIS's ETo. CIMIS provides ETo and solar radiation at a resolution of 2 km. CIMIS lists the following disclaimer about their data:
>This is a newly emerging technique and is in the process of being refined. Although the data quality presented here is acceptable for many applications, we do not guarantee its accuracy. Therefore, neither the CIMIS program, the Department of Water Resources (DWR), UC Davis, nor any other party who participated in the development of this product shall be responsible for errors in this data, nor for any resulting consequences from using this data. 

When we obtain the data, we store it internally as well as in a PostgresDB, along with all other relevant data. The only manipulation we do is apply the crop coefficient either selected by the user or the default crop coefficient as consulted on by our scientists.

### OpenET
OpenET's data is gathered via their API, you can view the documentation [here](https://openet.gitbook.io/docs). We are using the daily raster polygon timeseries API request to calculate both ensemble evapotranspiration (noted as ETa across our apps) and FrET (fractional ET, a ratio of ETa/ETo, labeled ETof on OpenET). CIMIS is the reference for both queries.
OpenET's has the following disclaimer about provisional data:
>Realtime OpenET data is considered “provisional” for the last 120 days. This data can and will change and is not considered stable/static/final. The two main sources for this change are the gridMET data not being finalized until after 60 days, and new Landsat images needing to be run through the models and used to interpolate previous months. To account for all of this, we make monthly updates of the last 3 to 4 month for all models and the ensemble.
We are currently, planning to refresh the last 3-4 months of our OpenET data monthly, similar to OpenET's approach. The issues with provisional data is more obvious when viewing FrET data.

### SAWS Towers
Our third source of data for our dashboard comes from our towers installed at the sites CSGrowers monitors. These towers were installed in the summer of 2025. They have sensors to measure weather, soil content, solar radiation, and water potential. CSGrowers gives you access to the most relevant data for growers. Towers collect data at either 30 or 60 minutes intervals and their daily values have been averaged for clarity. These towers are prone to data issues, but you can track your site's current issues in the "Known Issues" tab of the homepage.

### Credits
This app and repository was created and is managed by Audrey Petrosian.

Consultation on content and science provided by Nicolas Bambach and Kyle Knipper.

The towers were set-up and are monitored primarily by Sebastian Castro-Bustamante and Karem Meza Capcha. Special thanks to our "field dog" technicians (Peter Tolentino, Madeline Do, Tessa Guentensperger, and Carlos Perez) for all their work in and out of the field to help make projects like this possible.

Refernce ET provided by the California Irrigation Management Information System (CIMIS) a part of the California Department of Water Resoures, CIMIS can be accessed [here](https://cimis.water.ca.gov/Default.aspx).

Satelitte ET (ETa) and Fractional ET (FrET) are provided by OpenET, based on it's paper:
>Melton, F., et al., 2021. OpenET: Filling a Critical Data Gap in Water Management for the Western United States. Journal of the American Water Resources Association, 2021 Nov 2. doi:10.1111/1752-1688.12956

The towers were set-up and are monitored primarily by Sebastian Castro-Bustamante and Karem Meza Capcha. Special thanks to our "field dog" technicians for all their work in and out of the field to help make projects like this possible.

Special thanks to Mina Swintek for feedback on content, user interface, and bug testing.