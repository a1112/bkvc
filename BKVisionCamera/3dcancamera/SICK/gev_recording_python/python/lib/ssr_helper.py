# Copyright (c) 2023 SICK AG, Waldkirch
# SPDX-License-Identifier: Unlicense

baseXML = """<?xml version="1.0" encoding="UTF-8"?><SickRecord xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="SickRecord_schema.xsd">
<Revision>SICK V1.10 in work</Revision>
<SchemaChecksum>01020304050607080910111213141516</SchemaChecksum>
<ChecksumFile>checksum.hex</ChecksumFile>
<RecordDescription>
<Location>V3SXX5-1</Location>
<StartDateTime>2022-03-29T15:27:22+02:00</StartDateTime>
<EndDateTime>2022-03-29T15:27:26+02:00</EndDateTime>
<UserName>default</UserName>
<RecordToolName>Sick Scandata Recorder</RecordToolName>
<RecordToolVersion>v0.4</RecordToolVersion>
<ShortDescription></ShortDescription>
</RecordDescription>
<DataSets>
<DataSetStereo id="1" datacount="{NUM_FRAMES}">
<DeviceDescription>
<Family>V3SXX5-1</Family>
<Ident>Visionary-T Mini CX V3S105-1x 1.5.0.29745A</Ident>
<Version>3.0.0.2032</Version>
<SerialNumber>12345678</SerialNumber>
<LocationName>not defined</LocationName>
<IPAddress>192.168.1.10</IPAddress>
</DeviceDescription>
<FormatDescriptionDepthMap>
<TimestampUTC/>
<Version>uint16</Version>
<DataStream>
<Interleaved>false</Interleaved>
<Width>{WIDTH}</Width>
<Height>{HEIGHT}</Height>
<CameraToWorldTransform>
<value>1.000000</value>
<value>0.000000</value>
<value>0.000000</value>
<value>0.000000</value>
<value>0.000000</value>
<value>1.000000</value>
<value>0.000000</value>
<value>0.000000</value>
<value>0.000000</value>
<value>0.000000</value>
<value>1.000000</value>
<value>0.000000</value>
<value>0.000000</value>
<value>0.000000</value>
<value>0.000000</value>
<value>1.000000</value>
</CameraToWorldTransform>
<CameraMatrix>
<FX>{FX}</FX>
<FY>{FY}</FY>
<CX>{CX}</CX>
<CY>{CY}</CY>
</CameraMatrix>
<CameraDistortionParams>
<K1>{K1}</K1>
<K2>{K2}</K2>
<P1>{P1}</P1>
<P2>{P2}</P2>
<K3>{K3}</K3>
</CameraDistortionParams>
<FrameNumber>uint32</FrameNumber>
<Quality>uint8</Quality>
<Status>uint8</Status>
<PixelSize>
<X>{PixelSizeX}</X>
<Y>{PixelSizeY}</Y>
<Z>{PixelSizeZ}</Z>
</PixelSize>
{MAPSET}
</DataStream>
<DeviceInfo>
<Status>OK</Status>
</DeviceInfo>
</FormatDescriptionDepthMap>
<DataLink>
<FileName>data.bin</FileName>
<Checksum>01020304050607080910111213141516</Checksum>
</DataLink>
</DataSetStereo>
</DataSets>
</SickRecord>"""


distanceTemplate = '<Z decimalexponent="0" min="{MIN_DISTANCE}" max="{MAX_DISTANCE}">{DTYPE_DISTANCE}</Z>'
intensityTemplate = '<Intensity decimalexponent="0" min="{MIN_INTENISTY}" max="{MAX_INTENSITY}">{DTYPE_INTENISTY}</Intensity>'
confidenceTemplate = '<Confidence decimalexponent="0" min="{MIN_CONFIDENCE}" max="{MAX_CONFIDENCE}">{DTYPE_CONFIDENCE}</Confidence>'