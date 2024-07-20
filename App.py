import pandas as pd
from flask import Flask, request, send_file, render_template
from io import BytesIO, StringIO

app = Flask(__name__)

def allocate_rooms(group_file, hostel_file, num_hostels, num_rooms_per_hostel, max_room_capacity):
    # Read group and hostel data from CSV files
    group_df = pd.read_csv(group_file)
    hostel_df = pd.read_csv(hostel_file)

    # Create an empty DataFrame to store room allocation details
    allocation = pd.DataFrame(columns=['Group ID', 'Hostel Name', 'Room Number', 'Members Allocated'])

    # Initialize hostel capacity
    hostel_capacity = {f"Hostel {i+1}": num_rooms_per_hostel for i in range(num_hostels)}

    # Initialize hostel data
    hostel_data = hostel_df.copy()

    # Iterate over groups
    for group_id in group_df['Group ID'].unique():
        # Filter groups based on the current group ID
        current_group = group_df[group_df['Group ID'] == group_id]
        # Get the gender and number of members in the current group
        group_members = current_group['Members'].iloc[0]
        group_gender = current_group['Gender'].iloc[0]

        # Extract the number of boys and girls from the group gender
        boys, girls = 0, 0
        if '&' or 'and' in group_gender:
            boys_gender, girls_gender = group_gender.split(' & ') or group_gender.split(' and ')
            boys = int(boys_gender.split()[0])
            girls = int(girls_gender.split()[0])
        else:
            if 'Boys' in group_gender or 'Male' in group_gender:
                boys = int(group_gender.split()[0])
            elif 'Girls' in group_gender or 'Female' in group_gender:
                girls = int(group_gender.split()[0])

        # Allocate boys and girls to hostels
        remaining_members = boys + girls
        while remaining_members > 0:
            available_hostels = hostel_data[(hostel_data['Capacity'] >= 1) & (hostel_data['Capacity'] <= max_room_capacity)]
            if not available_hostels.empty:
                # Select the first available hostel and room
                hostel_name = available_hostels['Hostel Name'].iloc[0]
                room_number = available_hostels['Room Number'].iloc[0]

                # Allocate members to the current room
                members_allocated = min(max_room_capacity, remaining_members)
                allocation_row = pd.DataFrame({'Group ID': [group_id], 'Hostel Name': [hostel_name], 'Room Number': [room_number], 'Members Allocated': [members_allocated]})
                allocation = pd.concat([allocation, allocation_row], ignore_index=True)
                hostel_capacity[hostel_name] -= members_allocated
                available_hostels.loc[(available_hostels['Hostel Name'] == hostel_name) & (available_hostels['Room Number'] == room_number), 'Capacity'] -= members_allocated
                remaining_members -= members_allocated

                # Remove the allocated room from the available hostels
                available_hostels = available_hostels[(available_hostels['Hostel Name'] != hostel_name) | (available_hostels['Room Number'] != room_number)]
            else:
                # If no more rooms are available, raise an error
                raise ValueError(f"No available rooms for group {group_id} with {boys + girls} members.")

    return allocation

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        # Get uploaded CSV files
        group_file = request.files['group_file']
        hostel_file = request.files['hostel_file']

        # Check if files are valid CSV files
        if not group_file.filename.endswith('.csv') or not hostel_file.filename.endswith('.csv'):
            return 'Invalid file type. Please upload CSV files.', 400

        # Create file-like objects from the uploaded file contents
        group_string = group_file.read().decode('utf-8')
        hostel_string = hostel_file.read().decode('utf-8')

        # Create StringIO objects from the file-like objects
        group_io = StringIO(group_string)
        hostel_io = StringIO(hostel_string)

        # Allocate rooms
        allocation = allocate_rooms(group_io, hostel_io, num_hostels=10, num_rooms_per_hostel=100, max_room_capacity=100)

        # Create a CSV file for download
        csv_string = allocation.to_csv(index=False).encode('utf-8')
        csv_file = BytesIO(csv_string)
        csv_file.seek(0)

        # Return the CSV file for download
        return send_file(csv_file, as_attachment=True, mimetype='text/csv', download_name='room_allocation.csv')

    except ValueError as e:
        return str(e), 400
    except Exception as e:
        app.logger.error('An error occurred: %s', e)
        return 'An error occurred. Please try again.', 500

if __name__ == '__main__':
    app.run()
