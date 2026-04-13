import numpy as np
import base64
import struct
import os
from pathlib import Path

def generate_ecg_waveforms(duration=10, fs=250):
    t = np.linspace(0, duration, duration * fs)
    pulse_rate = 1.0 # 60 bpm
    
    lead_order = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']
    waveforms = {}
    
    for lead_name in lead_order:
        signal = np.zeros_like(t)
        for beat_time in np.arange(0.5, duration, 1.0/pulse_rate):
            # P wave (Small and standard)
            signal += 0.04 * np.exp(-((t - beat_time + 0.12)**2) / (2 * 0.015**2))
            
            # QRS complex
            qrs_sigma = 0.015
            r_amp = 1.0
            s_amp = -0.2
            
            if lead_name == 'V1': r_amp, s_amp = 0.25, -1.0 # Healthy
            elif lead_name == 'V2': r_amp, s_amp = 0.35, -1.2 # Healthy
            elif lead_name == 'V3': r_amp, s_amp = 0.05, -1.5 # Pathological (Poor Progression)
            elif lead_name == 'V4': r_amp, s_amp = 0.08, -1.0 # Pathological
            elif lead_name == 'V5': r_amp, s_amp = 1.2, -0.1
            elif lead_name == 'V6': r_amp, s_amp = 1.2, -0.1
            elif lead_name == 'I': r_amp, s_amp = 1.1, -0.1
            elif lead_name == 'II': r_amp, s_amp = 1.1, -0.1
            elif lead_name == 'III': r_amp, s_amp = 0.4, -0.4
            elif lead_name == 'aVR': r_amp, s_amp = -1.1, 0.2
            elif lead_name == 'aVL': r_amp, s_amp = 0.5, -0.1
            elif lead_name == 'aVF': r_amp, s_amp = 0.7, -0.3
                
            # R component
            signal += r_amp * np.exp(-((t - beat_time)**2) / (2 * qrs_sigma**2))
            # S component
            signal += s_amp * np.exp(-((t - beat_time - 0.02)**2) / (2 * qrs_sigma**2))
            
            # T wave
            t_amp = 0.2
            if lead_name == 'aVR': t_amp = -0.2
            signal += t_amp * np.exp(-((t - beat_time - 0.25)**2) / (2 * 0.04**2))
            
        # Add baseline noise
        signal += np.random.normal(0, 0.015, len(t))
        
        # Scaling to microvolts (1.0 = 1000uV)
        microvolts = signal * 1000
        bits = (microvolts / 4.88).astype(np.int16)
        
        # Encode to base64
        byte_data = bits.tobytes()
        waveforms[lead_name] = base64.b64encode(byte_data).decode('utf-8')
        
    return waveforms

def create_xml(filename, patient_id, waveforms):
    lead_data_template = """      <LeadData>
         <LeadByteCountTotal>5000</LeadByteCountTotal>
         <LeadSampleCountTotal>2500</LeadSampleCountTotal>
         <LeadAmplitudeUnitsPerBit>4.88</LeadAmplitudeUnitsPerBit>
         <LeadAmplitudeUnits>MICROVOLTS</LeadAmplitudeUnits>
         <LeadID>{lead_id}</LeadID>
         <LeadDataCRC32>0</LeadDataCRC32>
         <WaveFormData>
{waveform_data}
         </WaveFormData>
      </LeadData>"""

    all_leads_xml = ""
    for lead_id, data in waveforms.items():
        all_leads_xml += lead_data_template.format(lead_id=lead_id, waveform_data=data) + "\n"

    xml_content = f"""<?xml version="1.0" encoding="ISO-8859-1"?>
<!DOCTYPE RestingECG SYSTEM "restecg.dtd">
<RestingECG>
   <PatientDemographics>
      <PatientID>{patient_id}</PatientID>
      <PatientAge>65</PatientAge>
      <AgeUnits>YEARS</AgeUnits>
      <Gender>MALE</Gender>
   </PatientDemographics>
   <TestDemographics>
      <AcquisitionDate>01-22-2026</AcquisitionDate>
      <AcquisitionTime>10:00:00</AcquisitionTime>
      <Site>1</Site>
      <SiteName>General Hospital</SiteName>
      <Location>1</Location>
      <LocationName>Cardiology</LocationName>
   </TestDemographics>
   <RestingECGMeasurements>
      <VentricularRate>60</VentricularRate>
      <AtrialRate>60</AtrialRate>
      <PRInterval>160</PRInterval>
      <QRSDuration>90</QRSDuration>
      <QTCorrected>420</QTCorrected>
   </RestingECGMeasurements>
   <Diagnosis>
      <DiagnosisStatement>
         <StmtText>SINUS RHYTHM</StmtText>
      </DiagnosisStatement>
   </Diagnosis>
   <Waveform>
      <LeadCount>12</LeadCount>
      <!-- First waveform (dummy) -->
   </Waveform>
   <Waveform>
      <LeadCount>12</LeadCount>
{all_leads_xml}
   </Waveform>
</RestingECG>
"""
    with open(filename, "w") as f:
        f.write(xml_content)

if __name__ == "__main__":
    output_dir = Path("xml_input")
    output_dir.mkdir(exist_ok=True)
    
    ecg_id = "MUSE_example"
    waveforms = generate_ecg_waveforms()
    xml_path = output_dir / f"{ecg_id}.xml"
    create_xml(xml_path, "PATIENT001", waveforms)
    
    # Create labels.csv
    labels_path = output_dir / "labels.csv"
    labels_content = "ecg_id,lvef_lte_45,lvwt_gte_13,aortic_stenosis_moderate_severe,aortic_regurgitation_moderate_severe,mitral_regurgitation_moderate_severe,tricuspid_regurgitation_moderate_severe,pulmonary_regurgitation_moderate_severe,rv_systolic_dysfunction_moderate_severe,pericardial_effusion_moderate_large,pasp_gte_45,tr_max_gte_32,shd\n"
    labels_content += "MUSE_example,1,0,0,0,0,0,0,0,0,0,0,1\n"
    
    with open(labels_path, "w") as f:
        f.write(labels_content)
    
    print(f"Generated {xml_path} and {labels_path}")
