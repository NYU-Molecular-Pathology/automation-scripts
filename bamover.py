import os
import sys
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

PATHLAB_DIR = '/mnt/Z_drive/acc_pathology/molecular/MOLECULAR/IonTorrent/Oncomine_Patient_Data'
LOG_DIR  = '/home/ionadmin/logs/'

# set up logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO,
                    filename=os.path.join(LOG_DIR, "bamover-%s.log"%time.strftime("%Y%m%d-%H%M%S")),
                    filemode='w')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-1s: %(levelname)-1s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


class Watcher():

    def __init__(self, directory_to_watch):
        self.observer = Observer()
        self.directory_to_watch = directory_to_watch

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.directory_to_watch, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except Exception as e:
            self.observer.stop()
            logging.error("Error: %s" %e.message)

        self.observer.join()


class Handler(FileSystemEventHandler):

    @staticmethod
    def is_file_empty(a_file):
        try:
            return os.path.exists(a_file) and os.path.getsize(a_file) > 0
        except:
            return False

    def subdir_exist(sub_path):
        if (not os.path.exists(sub_path)):
            try:
                return os.system("echo '***' | sudo -S mkdir %s" % sub_path) == 0
            except:
                logging.error("failed to create subdirectory %s " % sub_path)
        return True

    @staticmethod
    def rsync_bam_file(bam_file):
        if Handler.is_file_empty(bam_file):
            run_id = os.path.dirname(bam_file).split("/")[-1].replace("Auto_user_", "")
            logging.info("RUN ID %s." % run_id)
            # create sub directory if not already exists
            dest_dir = os.path.join(PATHLAB_DIR, run_id)
            Handler.subdir_exist(dest_dir)
            rsync_cmd = "echo '***' | sudo -S rsync -thP %s %s" % (bam_file, dest_dir)
            logging.info("rsync command %s" % rsync_cmd)
            if (os.system(rsync_cmd) != 0):
                logging.error("rsync %s failed : " % bam_file)

    @staticmethod
    def on_any_event(event):
        if event.is_directory:
            return None

        elif event.event_type == 'created':
            # Take any action here when a file is first created.
            if event.src_path.endswith(".bam") or event.src_path.endswith(".bam.bai"):
                if "basecaller_results" not in event.src_path and "_tn_" not in event.src_path:
                    logging.info("Received created event - %s." % event.src_path)
        elif event.event_type == 'modified':
            if event.src_path.endswith(".bam") or event.src_path.endswith(".bam.bai"):
                if "basecaller_results" not in event.src_path and "_tn_" not in event.src_path:
                    # Taken any action here when a file is modified.
                    logging.info("Received modified event - %s." % event.src_path)
                    Handler.rsync_bam_file(event.src_path)

if __name__ == '__main__':
    directory_to_watch = sys.argv[1] if len(sys.argv) > 1 else '.'
    w = Watcher(directory_to_watch)
    w.run()
