import pyodbc

def migrate_appointments():
    """Migrate appointments table to use service_id consistently"""
    try:
        conn_str = 'Driver={SQL Server};Server=DESKTOP-Q7U1STD;Database=POSDB;Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        print('=== Migrating Appointments Table ===')

        # First, update service_id based on service_type for existing appointments
        print('\n1. Updating service_id for existing appointments...')

        # Get all services to create a mapping
        cursor.execute('SELECT id, service_name FROM services')
        services = cursor.fetchall()
        service_name_to_id = {service[1].lower(): service[0] for service in services}

        # Update appointments where service_id is NULL
        cursor.execute('SELECT id, service_type FROM appointments WHERE service_id IS NULL')
        null_service_id_apts = cursor.fetchall()

        for apt in null_service_id_apts:
            apt_id = apt[0]
            service_type = apt[1]

            # Try to match service_type to service_id
            if service_type:
                # Check if service_type is already a number (service_id)
                try:
                    service_id = int(service_type)
                    cursor.execute('UPDATE appointments SET service_id = ? WHERE id = ?', (service_id, apt_id))
                    print(f'  Updated appointment {apt_id}: service_type "{service_type}" -> service_id {service_id}')
                except ValueError:
                    # service_type is a name, try to find matching service
                    service_name_lower = service_type.lower()
                    if service_name_lower in service_name_to_id:
                        service_id = service_name_to_id[service_name_lower]
                        cursor.execute('UPDATE appointments SET service_id = ? WHERE id = ?', (service_id, apt_id))
                        print(f'  Updated appointment {apt_id}: service_type "{service_type}" -> service_id {service_id}')
                    else:
                        print(f'  Warning: Could not match service_type "{service_type}" for appointment {apt_id}')

        # Make service_type column nullable
        print('\n2. Making service_type column nullable...')
        try:
            cursor.execute('ALTER TABLE appointments ALTER COLUMN service_type NVARCHAR(100) NULL')
            print('  ✓ service_type column made nullable')
        except Exception as e:
            print(f'  Note: service_type column may already be nullable: {e}')

        # Verify the migration
        print('\n3. Verifying migration...')
        cursor.execute('SELECT id, service_type, service_id FROM appointments')
        all_appointments = cursor.fetchall()

        print('Final appointment service data:')
        for apt in all_appointments:
            print(f'  ID {apt[0]}: service_type={apt[1]}, service_id={apt[2]}')

        # Check for any remaining NULL service_id
        cursor.execute('SELECT COUNT(*) FROM appointments WHERE service_id IS NULL')
        null_count = cursor.fetchone()[0]
        if null_count > 0:
            print(f'\n⚠️  Warning: {null_count} appointments still have NULL service_id')
        else:
            print('\n✓ All appointments now have valid service_id')

        conn.commit()
        conn.close()
        print('\n=== Migration Complete ===')

    except Exception as e:
        print(f'Migration error: {e}')

if __name__ == "__main__":
    migrate_appointments()
