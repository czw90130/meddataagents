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

        # 初始化 SQLite 数据库连接
        self.conn = sqlite3.connect(self.db_name)
        self._initialize_db()

    def _initialize_db(self):
        """
        初始化 SQLite 数据库，创建记录处理文件和摘要的表。
        """
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

    def _calculate_hash(self, df):
        """
        计算 DataFrame 的 MD5 哈希值。

        :param df: 要计算哈希值的 DataFrame
        :return: 计算出的哈希值
        """
        hash_md5 = hashlib.md5()
        for row in df.itertuples(index=False):
            hash_md5.update(str(row).encode('utf-8'))
        return hash_md5.hexdigest()

    def _is_file_processed(self, file_path, sheet_name, new_hash):
        """
        检查文件和工作表是否已经处理过。

        :param file_path: 文件路径
        :param sheet_name: 工作表名称
        :param new_hash: 文件内容的新哈希值
        :return: 如果文件已处理且内容未变，返回 True；否则返回 False
        """
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
        更新指定文件和工作表的摘要。

        :param file_path: 文件路径
        :param sheet_name: 工作表名称
        :param summary: 新的摘要
        """
        update_query = """
        UPDATE processed_files 
        SET summary = ? 
        WHERE file_path = ? AND sheet_name = ?
        """
        self.conn.execute(update_query, (summary, file_path, sheet_name))
        self.conn.commit()

    def get_summary(self, file_path, sheet_name):
        """
        获取指定文件和工作表的摘要。

        :param file_path: 文件路径
        :param sheet_name: 工作表名称
        :return: 摘要字符串
        """
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

    def process_file(self, file_path):
        """
        处理单个文件。

        :param file_path: 文件路径
        """
        # 将文件路径转换为合法的表名
        table_name = file_path.replace(os.sep, "_").replace(":", "").replace(".", "_")

        # 处理Excel文件
        if file_path.endswith('.xlsx') and '~$' not in file_path:
            # 打开Excel文件
            excel_file = pd.ExcelFile(file_path)
            
            # 遍历Excel文件中的所有工作表
            for sheet_name in excel_file.sheet_names:
                # 读取当前工作表的数据
                df = excel_file.parse(sheet_name=sheet_name)
                
                # 计算数据的哈希值
                content_hash = self._calculate_hash(df)
                
                # 检查文件是否已经处理过且内容未变更
                if self._is_file_processed(file_path, sheet_name, content_hash):
                    print(f"Skipping unchanged file: {file_path} | {sheet_name}")
                    continue

                # 生成完整的表名（文件名_工作表名）
                full_table_name = f"{table_name}_{sheet_name}"
                
                # 将数据写入SQL数据库
                df.to_sql(full_table_name, self.conn, if_exists='replace', index=False)
                
                # 记录表信息
                self.table_info.append({
                    'file_path': file_path,
                    'sheet_name': sheet_name,
                    'table_name': full_table_name,
                    'columns': df.columns.tolist()
                })
                
                # 标记文件为已处理
                self._mark_file_as_processed(file_path, sheet_name, content_hash)

        # 处理CSV文件
        elif file_path.endswith('.csv'):
            # 读取CSV文件
            df = pd.read_csv(file_path)
            
            # 计算数据的哈希值
            content_hash = self._calculate_hash(df)
            
            # 检查文件是否已经处理过且内容未变更
            if self._is_file_processed(file_path, None, content_hash):
                print(f"Skipping unchanged file: {file_path}")
                return

            # 将数据写入SQL数据库
            df.to_sql(table_name, self.conn, if_exists='replace', index=False)
            
            # 记录表信息
            self.table_info.append({
                'file_path': file_path,
                'sheet_name': None,
                'table_name': table_name,
                'columns': df.columns.tolist()
            })
            
            # 标记文件为已处理
            self._mark_file_as_processed(file_path, None, content_hash)

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
        在所有表中搜索指定键值对。

        :param key: 搜索键
        :param value: 搜索值
        :return: 匹配结果的列表
        """
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

        :param table_name: 表名
        :return: 表头（列名）的列表
        """
        query = f"PRAGMA table_info('{table_name}')"
        cursor = self.conn.execute(query)
        columns = [info[1] for info in cursor.fetchall()]
        return columns

    def get_all_table_headers(self):
        """
        获取所有表的表头（列名）。

        :return: 包含每个表的表头信息的字典，键为表名，值为表头（列名）的列表
        """
        headers = {}
        for table in self.table_info:
            headers[table['table_name']] = self.get_table_header(table['table_name'])
        return headers

    def execute_query(self, query, params=None):
        """
        执行通用 SQL 查询。

        :param query: SQL 查询字符串
        :param params: 查询参数（可选）
        :return: 查询结果的列表
        """
        if params is None:
            params = ()
        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()
        return rows

    def close_connection(self):
        """
        关闭数据库连接。
        """
        self.conn.close()
        

# 示例用法
if __name__ == "__main__":
    processor = ExcelChunkProcessor()

    # 动态加载目录
    directory = sys.argv[1]  # 从命令行获取目录路径
    processor.process_directory(directory)

    # 动态加载单个文件
    # file_path = sys.argv[2]  # 从命令行获取文件路径
    # processor.process_file(file_path)

    # 获取所有表的表头
    all_headers = processor.get_all_table_headers()
    for table_name, headers in all_headers.items():
        print(f"Table: {table_name}, Headers: {headers}")

    # 搜索
    # key = '关联号'
    # value = 'ea6bbcbaf7444acf8ced823b98c8f21f'
    
    key = '患者标识'
    value = '66a4f976433ccc70b6a055345b22f74a'
    
    results = processor.search_across_tables(key, value)

    for result in results:
        file_path = result['file_path']
        sheet_name = result['sheet_name']
        row = result['row']
        print(f"Found in {file_path} | {sheet_name}: {row}")

    # # 更新摘要
    # processor.update_summary(file_path, 'Sheet1', 'Updated summary for Sheet1')
    # summary = processor.get_summary(file_path, 'Sheet1')
    # print(f"Summary for {file_path} | Sheet1: {summary}")

    # # 执行通用 SQL 查询
    # query = 'SELECT * FROM "your_table_name" WHERE "your_column_name" = ?'
    # params = ('your_value',)
    # general_query_results = processor.execute_query(query, params)
    # print(general_query_results)

    # 关闭数据库连接
    processor.close_connection()
