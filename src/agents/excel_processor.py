import os
import pandas as pd
import openpyxl
import sqlite3
import sys
import hashlib

class ExcelChunkProcessor:
    def __init__(self, db_name='data.db'):
        """
        初始化 ExcelChunkProcessor 对象。

        :param db_name: SQLite 数据库名称
        """
        self.db_name = db_name
        self.table_info = []
        self.connected = False
        self.conn = self.create_connection()
        self._initialize_db()

    def create_connection(self, db_file=None):
        """
        创建到SQLite数据库的连接。

        :param db_file: 数据库文件的路径
        :return: sqlite3.Connection 数据库连接对象，如果连接失败则返回None
        """
        if db_file is None:
            db_file = self.db_name
        try:
            conn = sqlite3.connect(db_file)
            self.connected = True
            return conn
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            self.connected = False
            return None

    def ensure_connected(self, ensure=False):
        """
        确保数据库连接有效，如果连接断开则尝试重新连接。

        :param ensure: 如果为True，在重连失败时抛出异常
        """
        try:
            self.conn.execute("SELECT 1")
        except sqlite3.Error:
            self.connected = False
            print("Connection was closed. Reconnecting...")
            self.conn = self.create_connection()
            if not self.connected and ensure:
                raise RuntimeError("Failed to re-establish database connection.")

    def _normalize_table_name(self, file_path, sheet_name=None):
        """
        生成标准化的表名，包括文件路径和工作表名（如果适用）。

        :param file_path: 文件路径
        :param sheet_name: 工作表名称（对于Excel文件）
        :return: 标准化的表名
        """
        normalized_path = file_path.replace(os.sep, "_").replace(":", "").replace(".", "_")
        if sheet_name:
            # 对工作表名称也进行标准化处理
            normalized_sheet = sheet_name.replace(" ", "_").replace(".", "_")
            return f"{normalized_path}_{normalized_sheet}"
        return normalized_path

    def _initialize_db(self):
        """
        初始化 SQLite 数据库，创建记录处理文件和摘要的表。
        """
        self.ensure_connected()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS processed_files (
            file_path TEXT PRIMARY KEY,
            sheet_name TEXT,
            content_hash TEXT,
            summary TEXT
        )
        """
        self.conn.execute(create_table_query)
        self.conn.commit()

    def calculate_hash(self, df):
        """
        计算 DataFrame 的 MD5 哈希值。

        :param df: 要计算哈希值的 DataFrame
        :return: 计算出的哈希值
        """
        hash_md5 = hashlib.md5()
        for row in df.itertuples(index=False):
            hash_md5.update(str(row).encode('utf-8'))
        return hash_md5.hexdigest()

    def is_file_processed(self, file_path, sheet_name, new_hash):
        """
        检查文件和工作表是否已经处理过。

        :param file_path: 文件路径
        :param sheet_name: 工作表名称
        :param new_hash: 文件内容的新哈希值
        :return: 如果文件已处理且内容未变，返回 True；否则返回 False
        """
        self.ensure_connected()
        query = "SELECT content_hash FROM processed_files WHERE file_path = ? AND sheet_name = ?"
        cursor = self.conn.execute(query, (file_path, sheet_name))
        result = cursor.fetchone()
        if result:
            stored_hash = result[0]
            return stored_hash == new_hash
        return False

    def _mark_file_as_processed(self, file_path, sheet_name, content_hash, summary="default summary (Empty)"):
        """
        标记文件和工作表为已处理，并添加摘要。

        :param file_path: 文件路径
        :param sheet_name: 工作表名称
        :param content_hash: 文件内容的哈希值
        :param summary: 表的摘要
        """
        self.ensure_connected()
        insert_query = """
        INSERT INTO processed_files (file_path, sheet_name, content_hash, summary) 
        VALUES (?, ?, ?, ?)
        ON CONFLICT(file_path) 
        DO UPDATE SET content_hash = excluded.content_hash, summary = excluded.summary
        """
        self.conn.execute(insert_query, (file_path, sheet_name, content_hash, summary))
        self.conn.commit()

    def update_summary(self, file_path, sheet_name, summary):
        """
        更新指定文件和工作表的摘要信息。

        此函数用于更新数据库中特定文件和工作表的摘要信息。摘要可以包含文件内容的简短描述、
        重要统计数据或其他相关元数据。更新摘要可以帮助用户快速了解文件内容，而无需重新处理整个文件。

        参数:
        file_path (str): 要更新摘要的文件的完整路径。
        sheet_name (str): Excel文件中的工作表名称。对于CSV文件，此参数应为None。
        summary (str): 新的摘要信息。应该是一个简洁但信息丰富的描述。

        返回:
        None

        示例:
        >>> processor = ExcelChunkProcessor()
        >>> processor.update_summary('/path/to/sales_data.xlsx', 'Q1_2023', 'Sales data for Q1 2023, total revenue: $1M')

        注意:
        - 在调用此函数之前，确保文件已经被处理并存在于数据库中。
        - 摘要信息应该简明扼要，但要包含足够的信息以便快速理解文件内容。
        - 对于CSV文件，sheet_name参数应设置为None。
        - 此操作会覆盖之前存储的摘要信息。
        """
        self.ensure_connected()
        update_query = """
        UPDATE processed_files 
        SET summary = ? 
        WHERE file_path = ? AND sheet_name = ?
        """
        self.conn.execute(update_query, (summary, file_path, sheet_name))
        self.conn.commit()

    def get_summary(self, file_path, sheet_name):
        """
        获取指定文件和工作表的摘要信息。

        此函数从数据库中检索特定文件和工作表的摘要信息。它可用于快速了解文件内容，而无需重新处理整个文件。

        参数:
        file_path (str): 要查询的文件的完整路径。
        sheet_name (str): Excel文件中的工作表名称。对于CSV文件，此参数应为None。

        返回:
        str or None: 如果找到摘要，则返回摘要字符串；如果未找到，则返回None。

        示例:
        >>> processor = ExcelChunkProcessor()
        >>> summary = processor.get_summary('/path/to/file.xlsx', 'Sheet1')
        >>> print(summary)
        'This sheet contains sales data for Q1 2023'

        注意:
        - 确保在调用此函数之前已经处理过相应的文件，否则可能返回None。
        - 对于CSV文件，sheet_name参数应设置为None。
        """
        self.ensure_connected()
        query = "SELECT summary FROM processed_files WHERE file_path = ? AND sheet_name = ?"
        cursor = self.conn.execute(query, (file_path, sheet_name))
        result = cursor.fetchone()
        return result[0] if result else None

    def read_excel_in_chunks(self, df, max_bytes, max_chunks, offset=0, skip_rows=None):
        """
        分块读取 DataFrame 数据。

        :param df: DataFrame 对象
        :param max_bytes: 每块数据的最大字节数
        :param max_chunks: 每次读取的最大块数
        :param offset: 起始行偏移值
        :param skip_rows: 需要跳过的行
        :return: 读取的数据块和下一个偏移值
        """
        df['row_number'] = df.index
        if skip_rows:
            df = df.drop(skip_rows)

        df = df.iloc[offset:]
        chunks = []
        current_chunk = []
        current_bytes = 0
        chunk_count = 0

        for i, row in df.iterrows():
            row_dict = row.to_dict()
            row_bytes = str(row_dict).encode('utf-8')
            row_size = len(row_bytes)

            if row_size > max_bytes:
                raise ValueError(f"单行数据量超过阈值：{row_size}/{max_bytes} bytes")

            if current_bytes + row_size > max_bytes or chunk_count >= max_chunks:
                chunks.append((current_chunk, offset + i))
                current_chunk = []
                current_bytes = 0
                chunk_count += 1

                if chunk_count >= max_chunks:
                    return chunks, offset + i

            current_chunk.append(row_dict)
            current_bytes += row_size

        if current_chunk:
            chunks.append((current_chunk, -1))

        return chunks, -1

    def process_file(self, file_path, summary=None):
        """
        处理单个文件，包括Excel和CSV文件。

        :param file_path: 文件路径
        :param summary: 文件摘要（可选）
        :return: 处理的表信息列表
        """
        self.ensure_connected()
        processed_info = []

        if file_path.endswith('.xlsx') and '~$' not in file_path:
            excel_file = pd.ExcelFile(file_path)
            for sheet_name in excel_file.sheet_names:
                df = excel_file.parse(sheet_name=sheet_name)
                content_hash = self.calculate_hash(df)
                normalized_table = self._normalize_table_name(file_path, sheet_name)
                if self.is_file_processed(normalized_table, sheet_name, content_hash):
                    print(f"Skipping unchanged file: {file_path} | {sheet_name}")
                    continue
                df.to_sql(normalized_table, self.conn, if_exists='replace', index=False)
                processed_info.append({
                    'file_path': file_path,
                    'sheet_name': sheet_name,
                    'table_name': normalized_table,
                    'columns': df.columns.tolist()
                })
                self._mark_file_as_processed(normalized_table, sheet_name, content_hash, summary)

        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            content_hash = self.calculate_hash(df)
            normalized_table = self._normalize_table_name(file_path)
            if self.is_file_processed(normalized_table, None, content_hash):
                print(f"Skipping unchanged file: {file_path}")
                return []
            df.to_sql(normalized_table, self.conn, if_exists='replace', index=False)
            processed_info.append({
                'file_path': file_path,
                'sheet_name': None,
                'table_name': normalized_table,
                'columns': df.columns.tolist()
            })
            self._mark_file_as_processed(normalized_table, None, content_hash, summary)

        self.table_info.extend(processed_info)
        return processed_info

    def process_directory(self, directory):
        """
        遍历目录并处理所有支持的文件（xlsx 和 csv）。

        :param directory: 目录路径
        """
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(('.xlsx', '.csv')):
                    file_path = os.path.join(root, file)
                    self.process_file(file_path)

    def search_across_tables(self, key, value):
        """
        在所有已处理的表中搜索指定的键值对。

        此函数遍历所有已处理的表，查找包含指定键值对的行。它对于在多个文件和表中查找特定数据非常有用。

        参数:
        key (str): 要搜索的列名（键）。
        value (Any): 要匹配的值。

        返回:
        list: 包含匹配结果的字典列表。每个字典包含以下键：
            - 'file_path': 匹配行所在的文件路径
            - 'sheet_name': 匹配行所在的工作表名称（对于CSV文件为None）
            - 'row': 包含匹配行所有列数据的字典

        示例:
        >>> processor = ExcelChunkProcessor()
        >>> results = processor.search_across_tables('employee_id', '12345')
        >>> for result in results:
        ...     print(f"Found in {result['file_path']} | {result['sheet_name']}: {result['row']}")

        注意:
        - 键值匹配可以在表总结(summary)中获得。
        - 搜索区分大小写。
        """
        self.ensure_connected()
        results = []
        query_template = 'SELECT * FROM "{}" WHERE "{}" = ?'
        for table in self.table_info:
            table_name = table['table_name']
            query = query_template.format(table_name, key)
            cursor = self.conn.execute(query, (value,))
            rows = cursor.fetchall()
            for row in rows:
                results.append({
                    'file_path': table['file_path'],
                    'sheet_name': table['sheet_name'],
                    'row': dict(zip(table['columns'], row))
                })
        return results

    def get_table_header(self, table_name):
        """
        获取指定表的表头（列名）。

        此函数返回数据库中特定表的所有列名。它对于了解表结构和可用的数据字段很有用。

        参数:
        table_name (str): 要获取表头的表名。这通常是文件名和工作表名的组合。

        返回:
        list: 包含表中所有列名的字符串列表。

        示例:
        >>> processor = ExcelChunkProcessor()
        >>> headers = processor.get_table_header('sales_data_2023_Sheet1')
        >>> print(headers)
        ['date', 'product', 'quantity', 'price', 'total']

        注意:
        - 确保提供的表名在数据库中存在，否则可能返回空列表。
        - 表名通常是文件名和工作表名的组合，可能包含下划线或其他分隔符。
        """
        self.ensure_connected()
        query = f"PRAGMA table_info('{table_name}')"
        cursor = self.conn.execute(query)
        columns = [info[1] for info in cursor.fetchall()]
        return columns

    def get_all_table_headers(self):
        """
        获取所有已处理表的表头（列名）。

        此函数返回数据库中所有表的表头信息。它提供了整个数据库结构的概览，对于理解和分析复杂的数据集很有帮助。

        参数:
        无

        返回:
        dict: 一个字典，其中键是表名，值是包含该表所有列名的列表。

        示例:
        >>> processor = ExcelChunkProcessor()
        >>> all_headers = processor.get_all_table_headers()
        >>> for table, headers in all_headers.items():
        ...     print(f"Table: {table}")
        ...     print(f"Columns: {headers}")
        ...     print("---")
        """
        self.ensure_connected()
        headers = {}
        for table in self.table_info:
            headers[table['table_name']] = self.get_table_header(table['table_name'])
        return headers

    def execute_query(self, query, params=None):
        """
        执行自定义SQL查询。

        此函数允许执行任意SQL查询，提供了直接访问数据库的灵活性。它可用于执行复杂的查询或数据操作，这些操作可能无法通过其他预定义方法实现。

        参数:
        query (str): 要执行的SQL查询字符串。
        params (tuple, optional): 查询参数的元组，用于参数化查询。默认为None。

        返回:
        list: 查询结果的行列表。每行都是一个元组，包含该行的所有列值。

        示例:
        >>> processor = ExcelChunkProcessor()
        >>> query = "SELECT * FROM sales_data WHERE total > ? AND date BETWEEN ? AND ?"
        >>> params = (1000, '2023-01-01', '2023-12-31')
        >>> results = processor.execute_query(query, params)
        >>> for row in results:
        ...     print(row)
        """
        self.ensure_connected()
        if params is None:
            params = ()
        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()
        return rows

    def close_connection(self):
        """
        关闭数据库连接。
        """
        if self.conn:
            self.conn.close()
            self.connected = False

# 示例用法
if __name__ == "__main__":
    processor = ExcelChunkProcessor()

    # 动态加载目录
    directory = sys.argv[1]  # 从命令行获取目录路径
    processor.process_directory(directory)

    # 获取所有表的表头
    all_headers = processor.get_all_table_headers()
    for table_name, headers in all_headers.items():
        print(f"Table: {table_name}, Headers: {headers}")

    # 搜索示例
    key = '患者标识'
    value = '66a4f976433ccc70b6a055345b22f74a'
    results = processor.search_across_tables(key, value)

    for result in results:
        file_path = result['file_path']
        sheet_name = result['sheet_name']
        row = result['row']
        print(f"Found in {file_path} | {sheet_name}: {row}")

    # 关闭数据库连接
    processor.close_connection()