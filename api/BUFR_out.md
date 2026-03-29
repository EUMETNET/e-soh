# E-SOH BUFR Output Format Sequence

E-SOH provides a BUFR output file when you select the BUFR format from the dropdown menu. The following table describes the BUFR sequence.

| Descriptor | Extended/Repeated | Name | Data Source | Note |
|------------|-------------------|------|-------------|------|
|||
||| **STATION IDENTIFICATION**
301150 || WIGOS identifier | metocean:wigosId | Mandatory
|| 0 01 125 | WIGOS identifier series
|| 0 01 126 | WIGOS issuer of identifier
|| 0 01 127 | WIGOS issue number
|| 0 01 128 | WIGOS local identifier (character)
301090 || Surface station identification || Mandatory
|| 3 01 004 | Surface station identification
|| 3 01 011 | Year, month, day
|| 3 01 012 | Hour, minute
|| 3 01 021 | Latitude/longitude (high accuracy)
|| 0 07 030 | Height of station ground above mean sea level
|| 0 07 031 | Height of barometer above mean sea level
||| **BASIC SURFACE OBSERVATIONS**
302031 || Pressure information | air_pressure, air_pressure_at_mean_sea_level | Optional
302032 || Temperature and humidity data | air_temperature, dew_point_temperature, relative_humidity | Optional
302033 || Visibility data || Optional
|||
||| **EXTREME TEMPERATURES** (Optional)
105000 || Replication descriptor
031001 || Delayed descriptor replication factor
|| 007032 | Height of sensor above local ground
|| 004025 | Time period or displacement
|| 012111 | Maximum temperature, at height and over period specified | air_temperature
|| 004025 | Time period or displacement
|| 012112 | Minimum temperature, at height and over period specified | air_temperature
|||
||| **WIND DATA** (Optional)
302042 ||| wind_speed, wind_from_direction, wind_speed_of_gust, wind_gust_from_direction
|||
||| **RADIATION** (Optional)
106000 || Replication descriptor
031101 || Delayed descriptor replication factor
|| 007032 | Height of sensor above local ground
|| 004025 | Time period or displacement
|| 014002 | Long-wave radiation, integrated over period specified | integral_wrt_time_of_surface_downwelling_longwave_flux_in_air
|| 014004 | Short-wave radiation, integrated over period specified | integral_wrt_time_of_surface_downwelling_shortwave_flux_in_air
|| 014012 | Net long-wave radiation, integrated over period specified | integral_wrt_time_of_surface_net_downward_longwave_flux
|| 014014 | Net short-wave radiation, integrated over period specified | integral_wrt_time_of_surface_net_downward_shortwave_flux
|||
||| **RADIATION** (Optional)
106000 || Replication descriptor
031101 || Delayed descriptor replication factor
|| 007032 | Height of sensor above local ground
|| 014002 | Downward long-wave radiation, integrated over period specified | integral_wrt_time_of_surface_net_downward_longwave_flux | Positive
|| 014002 | Upward long-wave radiation, integrated over period specified | integral_wrt_time_of_surface_net_downward_longwave_flux | Negative
|| 014004 | Downward short-wave radiation, integrated over period specified | integral_wrt_time_of_surface_downwelling_shortwave_flux_in_air | Positive
|| 014004 | Upward short-wave radiation, integrated over period specified | integral_wrt_time_of_surface_downwelling_shortwave_flux_in_air | Negative
|||
||| **PRECIPITATION** (Optional)
103000 || Replication descriptor
031001 || Delayed descriptor replication factor
|| 007032 | Height of sensor above local ground
|| 004025 | Time period or displacement
|| 013011 | Total precipitation/total, water equivalent | precipitation_amount
