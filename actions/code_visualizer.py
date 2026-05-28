"""
actions/code_visualizer.py — Algorithmic visualization data engine for IP Prime.

This is a premium action module for the IP Prime personal assistant suite.
"""

class CodeVisualizer:
    """Calculates step-by-step state frames for sorting and searching algorithms."""
    
    @staticmethod
    def bubble_sort(arr: list[int]) -> list[dict]:
        """
        Yields all execution frames for Bubble Sort.
        Each frame contains:
          - "array": Current list state
          - "compare": Indices currently being compared (tuple or list)
          - "swap": True if a swap occurred in this step
          - "sorted_indices": Set of indices that are fully sorted
        """
        frames = []
        n = len(arr)
        temp_arr = list(arr)
        
        # Initial frame
        frames.append({
            "array": list(temp_arr),
            "compare": [],
            "swap": False,
            "sorted_indices": []
        })
        
        sorted_indices = []
        for i in range(n):
            swapped = False
            for j in range(0, n - i - 1):
                # Frame showing comparison
                frames.append({
                    "array": list(temp_arr),
                    "compare": [j, j + 1],
                    "swap": False,
                    "sorted_indices": list(sorted_indices)
                })
                
                if temp_arr[j] > temp_arr[j + 1]:
                    temp_arr[j], temp_arr[j + 1] = temp_arr[j + 1], temp_arr[j]
                    swapped = True
                    # Frame showing swap occurrence
                    frames.append({
                        "array": list(temp_arr),
                        "compare": [j, j + 1],
                        "swap": True,
                        "sorted_indices": list(sorted_indices)
                    })
            
            sorted_indices.append(n - i - 1)
            if not swapped:
                break
                
        # Final frame
        frames.append({
            "array": list(temp_arr),
            "compare": [],
            "swap": False,
            "sorted_indices": list(range(n))
        })
        return frames

    @staticmethod
    def selection_sort(arr: list[int]) -> list[dict]:
        """
        Yields all execution frames for Selection Sort.
        Each frame contains:
          - "array": Current list state
          - "compare": (currentIndex, minIndex) being compared
          - "swap": True if swap occurred
          - "sorted_indices": Fully sorted indices
        """
        frames = []
        n = len(arr)
        temp_arr = list(arr)
        sorted_indices = []
        
        # Initial frame
        frames.append({
            "array": list(temp_arr),
            "compare": [],
            "swap": False,
            "sorted_indices": []
        })
        
        for i in range(n):
            min_idx = i
            for j in range(i + 1, n):
                frames.append({
                    "array": list(temp_arr),
                    "compare": [j, min_idx],
                    "swap": False,
                    "sorted_indices": list(sorted_indices)
                })
                if temp_arr[j] < temp_arr[min_idx]:
                    min_idx = j
                    
            if min_idx != i:
                temp_arr[i], temp_arr[min_idx] = temp_arr[min_idx], temp_arr[i]
                frames.append({
                    "array": list(temp_arr),
                    "compare": [i, min_idx],
                    "swap": True,
                    "sorted_indices": list(sorted_indices)
                })
            sorted_indices.append(i)
            
        # Final frame
        frames.append({
            "array": list(temp_arr),
            "compare": [],
            "swap": False,
            "sorted_indices": list(range(n))
        })
        return frames

    @staticmethod
    def binary_search(arr: list[int], target: int) -> list[dict]:
        """
        Yields all execution frames for Binary Search on a sorted array.
        Each frame contains:
          - "array": Current sorted array
          - "low": Low pointer index
          - "high": High pointer index
          - "mid": Midpointer index
          - "found": True if target is found
        """
        frames = []
        sorted_arr = sorted(arr)
        n = len(sorted_arr)
        low = 0
        high = n - 1
        
        while low <= high:
            mid = (low + high) // 2
            frames.append({
                "array": list(sorted_arr),
                "low": low,
                "high": high,
                "mid": mid,
                "found": sorted_arr[mid] == target
            })
            
            if sorted_arr[mid] == target:
                break
            elif sorted_arr[mid] < target:
                low = mid + 1
            else:
                high = mid - 1
                
        return frames
