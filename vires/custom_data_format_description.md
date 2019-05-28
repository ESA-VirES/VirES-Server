## VirES for Swarm - Custom File Format

This document describes format of the custom data files which can uploaded
to the VirES for Swarm service and visualized together with the Swarm,
models and auxiliary data offered by the service.

### Generic Data Description

The uploaded data file is expected to contain a multi-variate time series
of observations (records). Each of the records shall have a time-stamp and
geo-location (ITRF latitude, longitude and radius) and any number
of additional named variables.

The additional variables can be of a scalar or vector numerical type.

The vector variables will be decomposed to its scalar components.

While any input variable is allowed, there are special variables which
are interpreted similarly as the equivalent Swarm product variables, e.g.,
magnetic model residuals can be calculated for `F` and `B_NEC` variables.

The time-stamps do not need to be ordered.

### CDF File Format Description

Currently only data in the [CDF data format](https://cdf.gsfc.nasa.gov/) are supported.
The file structure is expected to be similar to the format of the Swarm satellite
products (e.g., [MAGx_LR_1B](https://earth.esa.int/web/guest/missions/esa-eo-missions/swarm/data-handbook/level-1b-product-definitions#Mag-L_Data_Set_Record.2C_MDR_MAG_LR))
or data downloaded via the VirES Web Client (https://vires.services)

Each separate CDF file variable is expected to have the same amount of records
as the time-stamp. If not, the variable is ignored.

The CDF variables are described in the following table.

#### CDF Variables
Field | Mandatory | Description | Units | Dim | Data Type
:-----|:---------:|:------------|:-----:|:---:|:---:
 **Timestamp** | yes | Time of observation | UTC | 1 | `CDF_EPOCH` 
 **Latitude** | yes | Position in ITRF – Geocentric latitude | UTC | 1 | `CDF_DOUBLE` 
 **Longitude** | yes | Position in ITRF – Geocentric longitude | UTC | 1 | `CDF_DOUBLE` 
 **Radius** | no | Position in ITRF – Radius (required to calculate QD-coordinates, MLT, and magnetic models) | UTC | 1 | `CDF_DOUBLE`
 **F** | no |  Magnetic field intensity (required to calculate model residuals) | nT | 1 | `CDF_DOUBLE`
 **B_NEC** | no | Magnetic field vector, NEC frame (required to calculate model residuals) | nT | 3 | `CDF_DOUBLE`
 *any* | no | arbitrary custom variable | *any* | *any* | *any CDF number data type*
