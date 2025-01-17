import streamlit as st
import subprocess
import re
import os
import zipfile
import numpy as np

# Function to run iccdump and capture the output
def extract_lut_from_icc(icc_file, iccdump_path):
    result = subprocess.run([iccdump_path, icc_file], capture_output=True, text=True)
    return result.stdout

# Function to extract all tags from the iccdump output
def extract_all_tags(lut_data):
    tags = re.findall(r"tag\s+(\d+):\s+sig\s+'(\S+)'", lut_data)
    return tags

# Function to extract LUT data from the iccdump output
def extract_lut_data(lut_data, lut_tag):
    lut_section = re.search(r"(tag .*\n.*sig\s+'{}'\n.*?)(?=tag|$)".format(lut_tag), lut_data, re.DOTALL)

    if lut_section:
        input_entries = re.findall(r"Input Table entries = (\d+)", lut_section.group(0))
        output_entries = re.findall(r"Output Table entries = (\d+)", lut_section.group(0))

        lut_values = re.findall(r"(\d+)", lut_section.group(0))
        lut_values = [int(i) for i in lut_values]  # Convert to integers
        
        bit_depth = 8  # Default to 8-bit
        if 'Lut16' in lut_section.group(0):
            bit_depth = 16
        
        max_value = 255 if bit_depth == 8 else 65535
        lut_values_normalized = [value / max_value for value in lut_values]
        
        return np.array(lut_values_normalized), input_entries, output_entries

    return None, None, None

# Streamlit UI
st.title("ICC Profile LUT Extractor")
st.markdown("Upload an ICC Profile and the folder containing the iccdump application.")

# File uploader for ICC profile
icc_file = st.file_uploader("Choose an ICC profile", type=["icc", "icm"])

# File uploader for the iccdump application folder
uploaded_folder = st.file_uploader("Upload the folder containing iccdump (ZIP file)", type=["zip"])

if icc_file and uploaded_folder:
    # Save and extract the uploaded folder
    extracted_folder = "uploaded_iccdump_folder"
    with open("uploaded_folder.zip", "wb") as f:
        f.write(uploaded_folder.read())
    
    with zipfile.ZipFile("uploaded_folder.zip", "r") as zip_ref:
        zip_ref.extractall(extracted_folder)

    # Locate the iccdump executable inside the specific path
    iccdump_path = os.path.join(extracted_folder, "Argyll_V3.3.0", "bin", "iccdump.exe")
    if not os.path.exists(iccdump_path):
        st.error("iccdump.exe not found in the uploaded folder. Please ensure it is located in `Argyll_V3.3.0/bin/`.")
    else:
        # Save the ICC profile temporarily
        icc_file_path = "temp_profile.icc"
        with open(icc_file_path, "wb") as f:
            f.write(icc_file.read())

        # Run iccdump and extract LUT data
        lut_data = extract_lut_from_icc(icc_file_path, iccdump_path)

        # Display the raw iccdump output
        st.subheader("Raw ICCDump Output")
        st.text(lut_data)  # Display raw output in the app

        # Extract all tags from the profile
        tags = extract_all_tags(lut_data)

        # Display tags and their information
        st.subheader("Tags and their corresponding LUTs")
        for tag in tags:
            tag_id, tag_sig = tag
            st.write(f"Processing tag `{tag_sig}` (ID: {tag_id})")

            # Only process LUT-related tags (e.g., A2B0, A2B1, etc.)
            if re.match(r"A2B\d", tag_sig) or re.match(r"B2A\d", tag_sig):
                lut_values, input_entries, output_entries = extract_lut_data(lut_data, tag_sig)
                
                if lut_values is not None:
                    lut_values_str = ", ".join([f"{value:.6f}" for value in lut_values[:10]])  # Print first 10 values with 6 decimal places
                    st.write(f"LUT Values for `{tag_sig}`: {lut_values_str}...")
                    st.write(f"Input Entries: {input_entries}")
                    st.write(f"Output Entries: {output_entries}")
                else:
                    st.write(f"No LUT data found for tag `{tag_sig}`.")
            else:
                st.write(f"Skipping tag `{tag_sig}`, not a LUT tag.")

    # Clean up temporary files
    os.remove("uploaded_folder.zip")
    os.remove(icc_file_path)
    if os.path.exists(extracted_folder):
        import shutil
        shutil.rmtree(extracted_folder)
else:
    st.write("Please upload both the ICC profile and the folder containing iccdump to proceed.")
