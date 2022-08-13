from utils import SkillPredictor
from unittest import TestCase

class TestPredictor(TestCase):
    def testResult(self):
        p = SkillPredictor()
        picked = [5458, 5459, 5460]
        avb = [5461, 5082, 5083, 5084]
        t  = p.predict(picked, avb)
        self.assertTrue(all([avb_skill in t for avb_skill in avb]))