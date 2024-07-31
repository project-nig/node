class Maintenance:
    """
    Class to manage the current Maintenance mode of the Node.
    """
    def __init__(self,*args, **kwargs):
        self.maintenance_mode=False

    def get_mode(self):
        return self.maintenance_mode

    def switch_on(self):
        self.maintenance_mode=True

    def switch_off(self):
        self.maintenance_mode=False


maintenance_mode=Maintenance()
