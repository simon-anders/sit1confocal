import czifile
import xml.etree.ElementTree as ET

metadata = czifile.CziFile("FH201025_GranB488_LAMP1594_TCR405_Phall647_5min_CD3stim_zoom2_pt_zstack1.czi").metadata()

root = ET.fromstring(metadata)

# Find all Channel elements under Dimensions/Channels
channels = root.findall('.//Dimensions/Channels/Channel')

# Extract and print data
print(f"{'Name':<15} {'Excitation (nm)':<20} {'Emission (nm)':<20} {'Detection (nm)':<20}")
print("-" * 75)

for ch in channels:
    name = ch.get('Name', 'N/A')
    exc = ch.find('ExcitationWavelength')
    em = ch.find('EmissionWavelength')
    det = ch.find('DetectionWavelength/Ranges')
    
    exc_val = float(exc.text) if exc is not None else 'N/A'
    em_val = float(em.text) if em is not None else 'N/A'
    det = ch.find('DetectionWavelength/Ranges')
    det_val0 = float(det.text.split('-')[0]) if det is not None else 'N/A'
    det_val1 = float(det.text.split('-')[1]) if det is not None else 'N/A'
    
    print(f"{name:<15} {exc_val:<20.1f} {em_val:<20.1f} {det_val0:<5.1f} -- {det_val1:<20.1f}")