## VirES for Swarm - Custom File Format

This document describes format of the custom data files which can uploaded
to the VirES for Swarm service and visualized together with the Swarm,
models and auxiliary data offered by the service.

### Generic Data Description

The uploaded data file is expected to contain a multi-variate time series
of observations (records). Each of the records shall have a time-stamp and
geo-location (ITRF latitude, longitude and radius) and any number
of additional named variables.

The ITRF latitude and longitude are mandatory.
**The radius is optional, but when not provided, the
geomagnetic models and magnetic coordinates requiring exact position
cannot be evaluated.** It is, therefore recommended to always provide
the complete set of coordinates, including the radius.

The additional variables can be of a scalar or vector numerical type.

The vector variables will be decomposed to its scalar components.

While any input variable is allowed, there are special variables which
are interpreted similarly as the equivalent Swarm product variables, e.g.,
magnetic model residuals can be calculated for `F` and `B_NEC` variables.

The time-stamps do not need to be ordered.

The data can be uploaded in the [CDF](https://cdf.gsfc.nasa.gov/) and [CSV](https://en.wikipedia.org/wiki/Comma-separated_values) data formats. Details of the data formats are described in the following sections.

### CDF File Format Description

The [CDF](https://cdf.gsfc.nasa.gov/) file structure is expected to be similar to the format of the Swarm satellite
products (e.g., [MAGx_LR_1B](https://earth.esa.int/web/guest/missions/esa-eo-missions/swarm/data-handbook/level-1b-product-definitions#Mag-L_Data_Set_Record.2C_MDR_MAG_LR))
or data downloaded via the VirES Web Client (https://vires.services)

Each separate CDF file variable is expected to have the same amount of records
as the time-stamp. If not, the variable is ignored.

The CDF variables are described in the following table.

#### CDF Variables
Field | Mandatory | Description | Units | Dim | Data Type
:-----|:---------:|:------------|:-----:|:---:|:---:
 **Timestamp** | yes | Time of observation | UTC | 1 | `CDF_EPOCH` 
 **Latitude** | yes | Position in ITRF – Geocentric latitude | deg | 1 | `CDF_DOUBLE` 
 **Longitude** | yes | Position in ITRF – Geocentric longitude | deg | 1 | `CDF_DOUBLE` 
 **Radius** | no | Position in ITRF – Radius (required to calculate QD-coordinates, MLT, and magnetic models) | m | 1 | `CDF_DOUBLE`
 **F** | no |  Magnetic field intensity (required to calculate model residuals) | nT | 1 | `CDF_DOUBLE`
 **B_NEC** | no | Magnetic field vector, NEC frame (required to calculate model residuals) | nT | 3 | `CDF_DOUBLE`
 *any* | no | arbitrary custom variable | *any* | *any* | *any CDF number data type*

### CSV File Format Description

The [CSV](https://en.wikipedia.org/wiki/Comma-separated_values) file structure
is similar to the CSV data downloaded from VirES (https://vires.services) and
these downloaded data can be uploaded back without modification.

The CSV file uses comma as a delimiter and it is required to have a header
(first line) defining the names of the records' fields. Each record is is
required to have the same number of values as the header.

#### Time-stamps

Each records is required to have a time-stamp defined as
- either [RFC-3339](https://tools.ietf.org/html/rfc3339) profile of
  [ISO-8601](https://en.wikipedia.org/wiki/ISO_8601) date-time
  (`Timestamp` variable), e.g., `2019-06-12T09:35:27.123Z`,
- or Modified Julian Date 2000 (`MJD2000` variable) defined as a decimal number
  of days since `2000-01-01T00:00:00Z`.

The Time-stamps' UTC offsets are accepted and interpreted (internally converted
to UTC). Time-stamps without a UTC offset are interpreted as UTC times, e.g.,
`2019-06-12T09:35:27.123` and `2019-06-12T09:35:27.123Z` are therefore the same
times.

If both `Timestamp` and `MJD200` are present, the `Timestamp` is used as
the record time-stamp.

#### Vector Fields

Vector fields are encoded as semicolon `;` separated list of values enclosed
by curly brackets `{}`, e.g.
```
{-2162.84267;-10248.5614;-45579.4719}
```

In the special case of the `B_NEC` vector variable, the `B_NEC` vector
is automatically composed from the `B_N`, `B_E`, `B_C` scalar component
if `B_NEC` is missing and all three `B_N`, `B_E`, `B_C` variables are present
in the CSV input data.

#### CDF Variables
Field | Mandatory | Description | Units | Dim | Data Type
:-----|:---------:|:------------|:-----:|:---:|:---:
 **Timestamp** | yes if `MJD2000` not present| Time of observation | UTC | 1 | RFC-3339
 **MJD2000** | yes if `Timestamp` not present| Time of observation | MJD2000 | 1 | float
 **Latitude** | yes | Position in ITRF – Geocentric latitude | deg | 1 | float
 **Longitude** | yes | Position in ITRF – Geocentric longitude | deg | 1 | float
 **Radius** | no | Position in ITRF – Radius (required to calculate QD-coordinates, MLT, and magnetic models) | m | 1 | float
 **F** | no |  Magnetic field intensity (required to calculate model residuals) | nT | 1 | float
 **B_NEC** | no | Magnetic field vector, NEC frame (required to calculate model residuals), automatically composed from `B_N`, `B_E`, `B_C` when present | nT | 3 | float
 **B_N** | no | Magnetic field vector's northing component | nT | 1 | float
 **B_E** | no | Magnetic field vector's easting component | nT | 1 | float
 **B_C** | no | Magnetic field vector's radial component (center oriented) | nT | 1 | float
 *any* | no | arbitrary custom variable | *any* | *any* | integer or float

The *float* means a decimal representation of the double-precision
floating-point number, e.g., `-8.5`, `1e-5`, `nan`, or `-inf`.





