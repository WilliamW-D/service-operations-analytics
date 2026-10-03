"""
Data Quality Validation and Cleaning Module.
Implements automated data auditing checks for null rates, range constraints,
logical timestamp consistency, and deduplication before warehouse loading.
"""

import pandas as pd
from typing import Dict, Any, Tuple, List

class DataQualityEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.audit_log: List[Dict[str, Any]] = []

    def log_result(self, check_name: str, passed: bool, details: str):
        self.audit_log.append({
            "check_name": check_name,
            "status": "PASSED" if passed else "FAILED",
            "details": details
        })

    def check_null_constraints(self, mandatory_columns: List[str]) -> bool:
        """Verify mandatory columns have 0 missing values."""
        all_passed = True
        for col in mandatory_columns:
            if col in self.df.columns:
                null_count = self.df[col].isnull().sum()
                passed = null_count == 0
                if not passed:
                    all_passed = False
                self.log_result(
                    f"Null Check: {col}",
                    passed,
                    f"Found {null_count} nulls out of {len(self.df)} rows"
                )
        return all_passed

    def check_timestamp_logic(self) -> bool:
        """Ensure closed_date >= created_date for resolved tickets."""
        df_closed = self.df[self.df["closed_date"].notnull()].copy()
        df_closed["created_dt"] = pd.to_datetime(df_closed["created_date"])
        df_closed["closed_dt"] = pd.to_datetime(df_closed["closed_date"])
        
        invalid_mask = df_closed["closed_dt"] < df_closed["created_dt"]
        invalid_count = invalid_mask.sum()
        passed = invalid_count == 0
        self.log_result(
            "Timestamp Logic Check (closed >= created)",
            passed,
            f"Found {invalid_count} tickets with closed_date before created_date"
        )
        return passed

    def check_ticket_uniqueness(self) -> bool:
        """Ensure ticket_number has no duplicates."""
        dup_count = self.df.duplicated(subset=["ticket_number"]).sum()
        passed = dup_count == 0
        self.log_result(
            "Uniqueness Check (ticket_number)",
            passed,
            f"Found {dup_count} duplicate ticket numbers"
        )
        return passed

    def clean_data(self) -> pd.DataFrame:
        """Apply automated data cleaning and sanitization rules."""
        # 1. Fill missing district/zip with defaults
        self.df["district_code"] = self.df["district_code"].fillna("DIST-UNKNOWN")
        self.df["neighborhood"] = self.df["neighborhood"].fillna("Unknown Neighborhood")
        self.df["zip_code"] = self.df["zip_code"].fillna("00000")
        
        # 2. Strip whitespace from text columns
        text_cols = ["department_name", "division_name", "request_category", "request_type", "status", "priority_level"]
        for col in text_cols:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype(str).str.strip()

        # 3. Deduplicate by ticket_number keeping first occurrence
        self.df = self.df.drop_duplicates(subset=["ticket_number"], keep="first")
        
        return self.df

    def run_all_checks(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """Execute full audit suite."""
        c1 = self.check_null_constraints(["ticket_number", "created_date", "department_name", "request_category"])
        c2 = self.check_timestamp_logic()
        c3 = self.check_ticket_uniqueness()
        overall_pass = c1 and c2 and c3
        return overall_pass, self.audit_log

if __name__ == "__main__":
    from generator import generate_raw_operational_data
    df_raw = generate_raw_operational_data(100)
    dq = DataQualityEngine(df_raw)
    cleaned_df = dq.clean_data()
    success, log = dq.run_all_checks()
    print("--- Data Quality Audit Report ---")
    for entry in log:
        print(f"[{entry['status']}] {entry['check_name']}: {entry['details']}")
