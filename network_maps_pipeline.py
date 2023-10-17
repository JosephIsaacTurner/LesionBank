import subprocess
import manage_aws_key

def main(input_directory="s3://lesionbucket/trace_input", output_directory="s3://lesionbucket/network_maps_output"):
    manage_aws_key.update_aws_secret_key()

    # Define the command as a list of strings
    cmd = [
        "python3", 
        "pfc-toolkit/src/pfctoolkit/scripts/connectome_precomputed",
        "-r", input_directory,
        "-c", "pfctoolkit_config/GSP1000_MF_91v_3209c.json",
        "-o", output_directory
    ]

    # Run the command using subprocess
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print("Error occurred while executing the command.")
    finally:
        manage_aws_key.remove_aws_secret_key()
    return output_directory

if __name__ == "__main__":
    main()
