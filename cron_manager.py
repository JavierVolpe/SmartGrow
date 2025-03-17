#!/usr/bin/env python3
"""
cron_manager.py

A module to manage the user's crontab from within a Python application.
It provides functionality to list, add, remove, and update cron jobs.
Note: This module uses the system 'crontab' command and is intended for Unix-like systems.
"""

import subprocess
import tempfile
import os

class CronManager:
    def __init__(self):
        pass

    def get_crontab(self) -> str:
        """
        Retrieve the current user's crontab content.

        Returns:
            str: The current crontab content. If no crontab exists, returns an empty string.
        """
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError:
            # If no crontab exists, "crontab -l" returns a non-zero exit status.
            return ""

    def write_crontab(self, content: str):
        """
        Write the provided content to the user's crontab.
        This version writes the content to a temporary file and then calls
        'crontab <tempfile>' so that the system's syntax check is applied.
        
        Args:
            content (str): The new crontab content.

        Raises:
            Exception: If writing to the crontab fails.
        """
        # Write content to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
            tf.write(content)
            temp_filename = tf.name

        # Attempt to install the new crontab from the temporary file
        process = subprocess.run(
            ["crontab", temp_filename],
            capture_output=True,
            text=True
        )

        # Clean up the temporary file
        os.unlink(temp_filename)

        if process.returncode != 0:
            raise Exception("Failed to write crontab: " + process.stderr)

    def add_job(self, job_line: str):
        """
        Add a new cron job line to the existing crontab.

        Args:
            job_line (str): A single cron job line, e.g. "0 5 * * * /path/to/script.sh".
        """
        current = self.get_crontab()
        if current and not current.endswith("\n"):
            current += "\n"
        new_content = current + job_line + "\n"
        self.write_crontab(new_content)

    def remove_job_by_index(self, index: int):
        """
        Remove a cron job by its index in the crontab list.

        Args:
            index (int): The index of the job to remove.
        """
        jobs = self.get_jobs()
        if 0 <= index < len(jobs):
            del jobs[index]
            new_content = "\n".join(jobs) + ("\n" if jobs else "")
            self.write_crontab(new_content)
        else:
            raise IndexError("Job index out of range.")

    def update_job_by_index(self, index: int, new_job_line: str):
        """
        Update a cron job at the specified index with a new job line.

        Args:
            index (int): The index of the job to update.
            new_job_line (str): The new cron job line.
        """
        jobs = self.get_jobs()
        if 0 <= index < len(jobs):
            jobs[index] = new_job_line
            new_content = "\n".join(jobs) + "\n"
            self.write_crontab(new_content)
        else:
            raise IndexError("Job index out of range.")

    def get_jobs(self):
        """
        Get a list of cron job lines.

        Returns:
            list: A list of cron job strings.
        """
        cron_raw = self.get_crontab().strip()
        return cron_raw.split("\n") if cron_raw else []

if __name__ == "__main__":
    # Example usage:
    cm = CronManager()
    print("Current crontab:")
    print(cm.get_crontab())
