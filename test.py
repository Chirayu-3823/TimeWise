class Solution:
    def successfulPairs(self, spells, potions, success: int):
        potions.sort()
        res = []
        for i in spells:
            l, r = 0, len(potions)-1
            while l <= r:
                mid = (l + r) // 2
                if i * potions[mid] >= success:
                    r = mid - 1
                else:
                    l = mid + 1
            res.append(len(potions)-l)
        return res

sol = Solution()
print(sol.successfulPairs([5,1,3], [1,2,3,4,5], 7))