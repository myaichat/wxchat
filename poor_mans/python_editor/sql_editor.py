import wx
import wx.aui
import wx.lib.agw.aui as aui
import  wx.grid             as  gridlib
import sys, re, os
import dbi
import odbc, time, datetime
from pprint import pprint
import images
from tc_lib import sub, send

#ddb='MRR_BI'
#duser='MRR_ETL_USER'
from db_utils import query
	
class AUIManager(aui.AuiManager):
	""" from MikeDriscoll's AUI AGW tutorial on wxPyWiki 
	suggested as a way to run multiple AUI instances """
	def __init__(self, managed_window):
		aui.AuiManager.__init__(self)
		self.SetManagedWindow(managed_window)

try:
	##raise ImportError     # for testing the alternate implementation
	from wx import stc
	from StyledTextCtrl_sql import SqlSTC

	class CodeEditor(SqlSTC):
		def __init__(self, parent, ID,style=wx.BORDER_NONE):
			SqlSTC.__init__(self, parent, ID, style=style)
			
			self.SetUpEditor()

		# Some methods to make it compatible with how the wxTextCtrl is used
		def SetValue(self, value):
			if wx.USE_UNICODE:
				value = value.decode('iso8859_1')
			val = self.GetReadOnly()
			#self.SetReadOnly(False)
			self.SetText(value)
			self.EmptyUndoBuffer()
			self.SetSavePoint()
			#self.SetReadOnly(val)

		#def SetEditable(self, val):
		#	self.SetReadOnly(not val)

		def IsModified(self):
			return self.GetModify()

		def Clear(self):
			self.ClearAll()

		def SetInsertionPoint(self, pos):
			self.SetCurrentPos(pos)
			self.SetAnchor(pos)

		def ShowPosition(self, pos):
			line = self.LineFromPosition(pos)
			#self.EnsureVisible(line)
			self.GotoLine(line)

		def GetLastPosition(self):
			return self.GetLength()

		def GetPositionFromLine(self, line):
			return self.PositionFromLine(line)

		def GetRange(self, start, end):
			return self.GetTextRange(start, end)

		def GetSelection(self):
			return self.GetAnchor(), self.GetCurrentPos()

		def SetSelection(self, start, end):
			self.SetSelectionStart(start)
			self.SetSelectionEnd(end)

		def SelectLine(self, line):
			start = self.PositionFromLine(line)
			end = self.GetLineEndPosition(line)
			self.SetSelection(start, end)
			
		def SetUpEditor(self):
			"""
			This method carries out the work of setting up the demo editor.            
			It's seperate so as not to clutter up the init code.
			"""
			import sql_keyword as keyword
			
			self.SetLexer(stc.STC_LEX_SQL)
			self.SetKeyWords(0, " ".join(keyword.kwlist))
	
			# Enable folding
			self.SetProperty("fold", "1" ) 

			# Highlight tab/space mixing (shouldn't be any)
			self.SetProperty("tab.timmy.whinge.level", "1")

			# Set left and right margins
			self.SetMargins(2,2)
	
			# Set up the numbers in the margin for margin #1
			self.SetMarginType(1, wx.stc.STC_MARGIN_NUMBER)
			# Reasonable value for, say, 4-5 digits using a mono font (40 pix)
			self.SetMarginWidth(1, 40)
	
			# Indentation and tab stuff
			self.SetIndent(4)               # Proscribed indent size for wx
			self.SetIndentationGuides(True) # Show indent guides
			self.SetBackSpaceUnIndents(True)# Backspace unindents rather than delete 1 space
			self.SetTabIndents(True)        # Tab key indents
			self.SetTabWidth(4)             # Proscribed tab size for wx
			self.SetUseTabs(False)          # Use spaces rather than tabs, or
											# TabTimmy will complain!    
			# White space
			self.SetViewWhiteSpace(False)   # Don't view white space
	
			# EOL: Since we are loading/saving ourselves, and the
			# strings will always have \n's in them, set the STC to
			# edit them that way.            
			self.SetEOLMode(wx.stc.STC_EOL_LF)
			self.SetViewEOL(False)
			
			# No right-edge mode indicator
			self.SetEdgeMode(stc.STC_EDGE_NONE)
	
			# Setup a margin to hold fold markers
			self.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
			self.SetMarginMask(2, stc.STC_MASK_FOLDERS)
			self.SetMarginSensitive(2, True)
			self.SetMarginWidth(2, 12)
	
			# and now set up the fold markers
			self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_BOXPLUSCONNECTED,  "white", "black")
			self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_BOXMINUSCONNECTED, "white", "black")
			self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNER,  "white", "black")
			self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNER,  "white", "black")
			self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,    "white", "black")
			self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_BOXPLUS,  "white", "black")
			self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_BOXMINUS, "white", "black")
	
			# Global default style
			if wx.Platform == '__WXMSW__':
				self.StyleSetSpec(stc.STC_STYLE_DEFAULT, 
								  'fore:#000000,back:#FFFFFF,face:Courier New')
			elif wx.Platform == '__WXMAC__':
				# TODO: if this looks fine on Linux too, remove the Mac-specific case 
				# and use this whenever OS != MSW.
				self.StyleSetSpec(stc.STC_STYLE_DEFAULT, 
								  'fore:#000000,back:#FFFFFF,face:Monaco')
			else:
				defsize = wx.SystemSettings.GetFont(wx.SYS_ANSI_FIXED_FONT).GetPointSize()
				self.StyleSetSpec(stc.STC_STYLE_DEFAULT, 
								  'fore:#000000,back:#FFFFFF,face:Courier,size:%d'%defsize)
	
			# Clear styles and revert to default.
			self.StyleClearAll()

			# Following style specs only indicate differences from default.
			# The rest remains unchanged.

			# Line numbers in margin
			self.StyleSetSpec(wx.stc.STC_STYLE_LINENUMBER,'fore:#000000,back:#99A9C2')    
			# Highlighted brace
			self.StyleSetSpec(wx.stc.STC_STYLE_BRACELIGHT,'fore:#00009D,back:#FFFF00')
			# Unmatched brace
			self.StyleSetSpec(wx.stc.STC_STYLE_BRACEBAD,'fore:#00009D,back:#FF0000')
			# Indentation guide
			self.StyleSetSpec(wx.stc.STC_STYLE_INDENTGUIDE, "fore:#CDCDCD")
	
			# SQL styles
			self.StyleSetSpec(wx.stc.STC_SQL_DEFAULT, 'fore:#000000')
			# Comments
			self.StyleSetSpec(wx.stc.STC_SQL_COMMENTLINE,  'fore:#006600') #back:#F0FFF0,back:#FFFFCC
			self.StyleSetSpec(wx.stc.STC_SQL_COMMENT, 'fore:#006600')
			self.StyleSetSpec(wx.stc.STC_SQL_COMMENTDOC, 'fore:#006600')
			# Numbers
			self.StyleSetSpec(wx.stc.STC_SQL_NUMBER, 'fore:#007F7F')
			# Strings and characters
			self.StyleSetSpec(wx.stc.STC_SQL_STRING, 'fore:#FF0000')
			self.StyleSetSpec(wx.stc.STC_SQL_CHARACTER, 'fore:#FF0000')
			# Keywords
			self.StyleSetSpec(wx.stc.STC_SQL_WORD, 'fore:#00009D,bold')
			self.StyleSetSpec(wx.stc.STC_SQL_WORD2, 'fore:#00009D,bold')
			# Triple quotes
			self.StyleSetSpec(wx.stc.STC_SQL_QUOTEDIDENTIFIER, 'fore:#800080,back:#FFFFEA')
			self.StyleSetSpec(wx.stc.STC_SQL_SQLPLUS, 'fore:#800080,back:#FFFFEA')
			# Class names
			self.StyleSetSpec(wx.stc.STC_SQL_COMMENTLINEDOC, 'fore:#0000FF,bold')
			# Function names
			self.StyleSetSpec(wx.stc.STC_SQL_COMMENTDOCKEYWORD, 'fore:#008080,bold')
			# Operators
			self.StyleSetSpec(wx.stc.STC_SQL_OPERATOR, 'fore:#800000,bold')
			# Identifiers. I leave this as not bold because everything seems
			# to be an identifier if it doesn't match the above criterae
			self.StyleSetSpec(wx.stc.STC_SQL_IDENTIFIER, 'fore:#000000')

			# Caret color
			self.SetCaretForeground("BLACK")
			# Selection background
			self.SetSelBackground(1, '#66CCFF')

			self.SetSelBackground(True, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
			self.SetSelForeground(True, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))

		def RegisterModifiedEvent(self, eventHandler):
			self.Bind(wx.stc.EVT_STC_CHANGE, eventHandler)


except ImportError:
		print 'cannot init class CodeEditor(SqlSTC)'
		sys.exit(1)
			
class SimpleGrid(gridlib.Grid): ##, mixins.GridAutoEditMixin):
	def __init__(self, parent, log):
		gridlib.Grid.__init__(self, parent, -1)
		##mixins.GridAutoEditMixin.__init__(self)
		self.log = log
		self.moveTo = None

		self.Bind(wx.EVT_IDLE, self.OnIdle)

		rows=10
		cols=25
		self.CreateGrid(rows, cols)#, gridlib.Grid.SelectRows)
		self.SetColFormatFloat(2,-1,2)
		self.surrent_sql=None
		self.connect_as=None
		
		# test all the events
		self.Bind(gridlib.EVT_GRID_CELL_LEFT_CLICK, self.OnCellLeftClick)
		self.Bind(gridlib.EVT_GRID_CELL_RIGHT_CLICK, self.OnCellRightClick)
		self.Bind(gridlib.EVT_GRID_CELL_LEFT_DCLICK, self.OnCellLeftDClick)
		self.Bind(gridlib.EVT_GRID_CELL_RIGHT_DCLICK, self.OnCellRightDClick)

		self.Bind(gridlib.EVT_GRID_LABEL_LEFT_CLICK, self.OnLabelLeftClick)
		self.Bind(gridlib.EVT_GRID_LABEL_RIGHT_CLICK, self.OnLabelRightClick)
		self.Bind(gridlib.EVT_GRID_LABEL_LEFT_DCLICK, self.OnLabelLeftDClick)
		self.Bind(gridlib.EVT_GRID_LABEL_RIGHT_DCLICK, self.OnLabelRightDClick)

		self.Bind(gridlib.EVT_GRID_ROW_SIZE, self.OnRowSize)
		self.Bind(gridlib.EVT_GRID_COL_SIZE, self.OnColSize)

		self.Bind(gridlib.EVT_GRID_RANGE_SELECT, self.OnRangeSelect)
		self.Bind(gridlib.EVT_GRID_CELL_CHANGE, self.OnCellChange)
		self.Bind(gridlib.EVT_GRID_SELECT_CELL, self.OnSelectCell)

		self.Bind(gridlib.EVT_GRID_EDITOR_SHOWN, self.OnEditorShown)
		self.Bind(gridlib.EVT_GRID_EDITOR_HIDDEN, self.OnEditorHidden)
		self.Bind(gridlib.EVT_GRID_EDITOR_CREATED, self.OnEditorCreated)
		self.Bind(wx.EVT_KEY_DOWN, self.onTextKeyEvent)
		#wx.EVT_KEY_DOWN, self.onTextKeyEvent,

	def UpdateGrid(self, sql):
		db = odbc.odbc("Driver={NetezzaSQL};servername=lltws01ypdbd1v;port=5480;database=MRR_BI;username=MRR_ETL_USER;password=Nynj2011;")
		cur = db.cursor()
		#select cob_dt_id,count(*) from CUBE_DATA_20130702173203_ab group by cob_dt_id;
		#sql="select * from CUBE_DATA_20130702173203_ab LIMIT 15;"
		pprint(sql);
		#pprint("select * from CUBE_DATA_20130702173203_ab LIMIT 15;");
		#cleanup
		sql = re.sub('(\n(\s+)?\n)', '',sql)
		sql = re.sub('[\r\n]+', '',sql)
		print '#'*20
		pprint (sql)
		print '#'*20
		print '%d' % cur.execute ("%s" % sql)
		
		#print [d[0] for d in c.description]
		#print 'cur.rowcount= ',cur.rowcount
		rs=cur.fetchall()

		rows=len(rs)
		cols=len(rs[0])
		print "new:  ", rows, cols
		print "Existing:  ",self.GetNumberRows(), self.GetNumberCols()
		#pprint(dir(self))
		self.ClearGrid()
		#self.DeleteGrid()
		newcols=cols-self.GetNumberCols()
		if newcols>=0: self.AppendCols(newcols)
		else: self.DeleteCols(cols,newcols)
		newrows=rows-self.GetNumberRows()
		if newrows>=0: self.AppendRows(newrows)
		else: self.DeleteRows(rows,newrows)
		#self.CreateGrid(rows, cols)#, gridlib.Grid.SelectRows)
		#self.EnableEditing(False)
		
		for r in range(rows):			
			for c in range(cols):			
				#print rs[r][c]
				self.SetCellValue(r, c, str(rs[r][c]))
			
		headers=cur.description
		for d in range(len(headers)):
			#print headers[d]
			self.SetColLabelValue(d, headers[d][0])

		self.SetColLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_BOTTOM)
		print "Updating grid"

	def UpdateLimitedGrid(self, sql,connect_as):
		#global d
		(db, user) = connect_as
		assert sql, 'sql statement is not defined'
		assert db, 'Database is not set'
		assert user, 'User is not set'
		self.surrent_sql=sql
		self.connect_as=connect_as
		print 'Connecting to %s as %s ...' % (db, user)		
		conn = "Driver={NetezzaSQL};servername=lltws01ypdbd1v;port=5480;database=%s;username=%s;password=Nynj2011;" % (db,user)
		ip = 'localhost'
		conn="Driver={Microsoft ODBC for Oracle};Server=(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=%s)(PORT=1521))(CONNECT_DATA=(SID=orcl)));Uid=scott;Pwd=tiger;" % (ip)
		conn="Driver={Microdsoft ODBC for Oracle};Server=localhost:1521/ORCL.localhost;DNS=Oracle11G;UID=scott;PWD=tiger;" 
		odb = odbc.odbc(conn)
		cur = odb.cursor()
		#select cob_dt_id,count(*) from CUBE_DATA_20130702173203_ab group by cob_dt_id;
		#sql="select * from CUBE_DATA_20130702173203_ab LIMIT 15;"
		pprint(sql);
		#pprint("select * from CUBE_DATA_20130702173203_ab LIMIT 15;");
		#cleanup
		#sql = re.sub('(\n(\s+)?\n)', '',sql)
		#sql = re.sub('[\r\n]+', '',sql)
		print '#'*20
		pprint (sql)
		print '#'*20
		#print 'before exec'
		status=0
		rowcount=0
		headers=[]
		err=''
		i=1
		#rowcount=0
		self.ClearGrid()
		try:
			d = PBI.PyBusyInfo('Executing query...', title='NZ SQL')
			wx.Yield()
			status=cur.execute ("%s" % sql)
			pprint(dir(cur))
			print cur.description
			#print 'cur.rowcount= ',cur.arraysize
		except dbi.progError, e:
			del d
			print 'dbi.progError! '
			status=1
			err=e
		except dbi.internalError, e:
			del d
			print 'dbi.internalError! ', status
			status=1
			err=e
			
		#print 'after exec: ', status
		
		#print [d[0] for d in c.description]

			
		if err: # or (not status and not cur.description) :
			#print(dir(d))
			print '#'*60
			print err
			print '#'*60
			print status
			self.ClearGrid()
			#self.DeleteCols(0,self.GetNumberCols(), True)
			print 'self.GetNumberCols()= ',self.GetNumberCols()
		else:
			headers=cur.description
			if headers:
				print 'self.GetNumberCols()= ',self.GetNumberCols()
				print "Status: ", status
				print dir(cur)
				print 'fetch# %d' % i
				try:
					rs=cur.fetchone()
				except dbi.progError, e:
					del d
					print 'dbi.progError! '
					status=1
					err=e
					
				except dbi.internalError, e:
					del d
					print 'dbi.internalError! ', status
					status=1
					err=e	
				if err: # or (not status and not cur.description) :
					#print(dir(d))
					print '#'*60
					print err
					print '#'*60
					print status
					self.ClearGrid()
					#self.DeleteCols(0,self.GetNumberCols(), True)
					print 'self.GetNumberCols()= ',self.GetNumberCols()					
				else:
					#print(dir(self))
					
					if rs:
						
						self.ForceRefresh()
						self.BeginBatch()
						#self.ClearGrid()
						while rs and i<101:
							#self.BeginBatch()
							rows=i # len(rs)
							cols=len(rs)
							#print "new:  ", rows, cols
							#print "Existing:  ",self.GetNumberRows(), self.GetNumberCols()
							#			
							#self.DeleteGrid()
							#print "newrows1"

							if i==1:
								attr = gridlib.GridCellAttr()
								#pprint(dir(attr))
							newcols=cols-self.GetNumberCols()
							#print 'Columns1: ', cols, self.GetNumberCols(), newcols
							if newcols>=0: 					
								if newcols>0: 
									#print "appending cols1"
									self.AppendCols(newcols)
								#else:
								#	#print "no cols change 1"
								#	pass
							else:
								#print "deleting cols1"
								self.DeleteCols(cols,newcols)

							newrows=rows-self.GetNumberRows()
							#print 'Rows1: ', rows, self.GetNumberRows(), newrows
							if newrows>=0: 
								#print 'appending rows 1:', newrows
								self.AppendRows(newrows)
							else: self.DeleteRows(rows,newrows)
							
							#self.CreateGrid(rows, cols)#, gridlib.Grid.SelectRows)
							#self.EnableEditing(False)
							
							#for r in range(rows):	
							#print 'range cols1: ', i
							#print rs
							for c in range(cols):			
								#print 1,c,str(rs[c])
								#print 'setting val 1: ', i-1, c, str(rs[c])
								self.SetCellValue(i-1, c, str(rs[c]))
								#self.Refresh()
							#headers=cur.description
							for d in range(len(headers)):
								#print headers[d]
								self.SetColLabelValue(d, headers[d][0])

							self.SetColLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_BOTTOM)
							#print "Updating limited grid"
							i+=1
							#self.EndBatch()
							
							rs=cur.fetchone()
							
							#time.sleep(5)
						self.EndBatch()
						rowcount=i-1
					else:
						#self.BeginBatch()
						if self.GetNumberRows()>0:
							#self.DeleteRows(0,self.GetNumberRows())
							#self.UpdateAttrRows(0,self.GetNumberRows())
							#msg = wx.grid.GridTableMessage(self.GetTable(), wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, 0,self.GetNumberRows() )
							#self.GetTable().GetView().ProcessTableMessage(wx.grid.GridTableMessage( self.GetTable(),wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED,  self.GetNumberRows()))
							#self.ForceRefresh()
							#self.Refresh()
							#pprint(dir(self.GetTable()))
							self.ClearGrid()
							
						#self.ForceRefresh()
						#headers=cur.description
						cols=len(headers)
						newcols=cols-self.GetNumberCols()
						print 'Columns0: ', cols, self.GetNumberCols(), newcols
						#pprint(headers)
						#print 'Columns1: ', cols, self.GetNumberCols(), newcols
						#self.ResetGrid()
						if newcols>=0: 					
							if newcols>0: 
								print "appending cols1"
								self.AppendCols(newcols)
							#else:
							#	#print "no cols change 1"
							#	pass
						else:
							print "deleting cols1"
							self.DeleteCols(cols,newcols)	
						#self.ResetGrid()
						print 'after append cols'
						if self.GetNumberCols()>0:
							for d in range(len(headers)):
								#print headers[d]
								self.SetColLabelValue(d, headers[d][0])
						#pass
						#self.EndBatch()
						#self.ForceRefresh()
						err='0 records returned.'
			else:
				del d
				print 'Success status= ',status
				print err
				print cur.error()
				print 
				if status>0:
					print 'Rows affected: %d' % status
					#rowcount=status
				#err='Success.'
			#pprint(dir(self))	
		return (status, err, rowcount,headers)
	def ClearGrid(self):
		self.GetTable().Clear()		
		numr=self.GetNumberRows()
		if numr<0: numr=0;
		print "after delete: ", numr
		if numr>0:
			self.DeleteRows(0,numr)
			self.GetTable().GetView().ProcessTableMessage(wx.grid.GridTableMessage( self.GetTable(),wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED,  self.GetNumberRows(),1))
		print "after delete fix: ", self.GetNumberRows()	
	def OnCellLeftClick(self, evt):
		self.log.write("OnCellLeftClick: (%d,%d) %s\n" %
					   (evt.GetRow(), evt.GetCol(), evt.GetPosition()))
		evt.Skip()

	def OnCellRightClick(self, evt):
		self.log.write("OnCellRightClick: (%d,%d) %s\n" %
					   (evt.GetRow(), evt.GetCol(), evt.GetPosition()))
		evt.Skip()

	def OnCellLeftDClick(self, evt):
		self.log.write("OnCellLeftDClick: (%d,%d) %s\n" %
					   (evt.GetRow(), evt.GetCol(), evt.GetPosition()))
		evt.Skip()

	def OnCellRightDClick(self, evt):
		self.log.write("OnCellRightDClick: (%d,%d) %s\n" %
					   (evt.GetRow(), evt.GetCol(), evt.GetPosition()))
		evt.Skip()

	def OnLabelLeftClick(self, evt):
		self.log.write("OnLabelLeftClick: (%d,%d) %s\n" %
					   (evt.GetRow(), evt.GetCol(), evt.GetPosition()))
		evt.Skip()

	def OnLabelRightClick(self, evt):
		self.log.write("OnLabelRightClick: (%d,%d) %s\n" %
					   (evt.GetRow(), evt.GetCol(), evt.GetPosition()))
		evt.Skip()

	def OnLabelLeftDClick(self, evt):
		self.log.write("OnLabelLeftDClick: (%d,%d) %s\n" %
					   (evt.GetRow(), evt.GetCol(), evt.GetPosition()))
		evt.Skip()

	def OnLabelRightDClick(self, evt):
		self.log.write("OnLabelRightDClick: (%d,%d) %s\n" %
					   (evt.GetRow(), evt.GetCol(), evt.GetPosition()))
		evt.Skip()

	def OnRowSize(self, evt):
		self.log.write("OnRowSize: row %d, %s\n" %
					   (evt.GetRowOrCol(), evt.GetPosition()))
		evt.Skip()

	def OnColSize(self, evt):
		self.log.write("OnColSize: col %d, %s\n" %
					   (evt.GetRowOrCol(), evt.GetPosition()))
		evt.Skip()

	def OnRangeSelect(self, evt):
		if evt.Selecting():
			msg = 'Selected'
		else:
			msg = 'Deselected'
		self.log.write("OnRangeSelect: %s  top-left %s, bottom-right %s\n" %
						   (msg, evt.GetTopLeftCoords(), evt.GetBottomRightCoords()))
		evt.Skip()


	def OnCellChange(self, evt):
		self.log.write("OnCellChange: (%d,%d) %s\n" %
					   (evt.GetRow(), evt.GetCol(), evt.GetPosition()))

		# Show how to stay in a cell that has bad data.  We can't just
		# call SetGridCursor here since we are nested inside one so it
		# won't have any effect.  Instead, set coordinates to move to in
		# idle time.
		value = self.GetCellValue(evt.GetRow(), evt.GetCol())

		if value == 'no good':
			self.moveTo = evt.GetRow(), evt.GetCol()


	def OnIdle(self, evt):
		if self.moveTo != None:
			self.SetGridCursor(self.moveTo[0], self.moveTo[1])
			self.moveTo = None

		evt.Skip()


	def OnSelectCell(self, evt):
		if evt.Selecting():
			msg = 'Selected'
		else:
			msg = 'Deselected'
		self.log.write("OnSelectCell: %s (%d,%d) %s\n" %
					   (msg, evt.GetRow(), evt.GetCol(), evt.GetPosition()))

		# Another way to stay in a cell that has a bad value...
		row = self.GetGridCursorRow()
		col = self.GetGridCursorCol()

		if self.IsCellEditControlEnabled():
			self.HideCellEditControl()
			self.DisableCellEditControl()

		value = self.GetCellValue(row, col)

		if value == 'no good 2':
			return  # cancels the cell selection

		evt.Skip()


	def OnEditorShown(self, evt):
		if evt.GetRow() == 6 and evt.GetCol() == 3 and \
		   wx.MessageBox("Are you sure you wish to edit this cell?",
						"Checking", wx.YES_NO) == wx.NO:
			evt.Veto()
			return

		self.log.write("OnEditorShown: (%d,%d) %s\n" %
					   (evt.GetRow(), evt.GetCol(), evt.GetPosition()))
		evt.Skip()


	def OnEditorHidden(self, evt):
		if evt.GetRow() == 6 and evt.GetCol() == 3 and \
		   wx.MessageBox("Are you sure you wish to  finish editing this cell?",
						"Checking", wx.YES_NO) == wx.NO:
			evt.Veto()
			return

		self.log.write("OnEditorHidden: (%d,%d) %s\n" %
					   (evt.GetRow(), evt.GetCol(), evt.GetPosition()))
		evt.Skip()


	def OnEditorCreated(self, evt):
		self.log.write("OnEditorCreated: (%d, %d) %s\n" %
					   (evt.GetRow(), evt.GetCol(), evt.GetControl()))

	def onTextKeyEvent(self, event):
		keycode = event.GetKeyCode()
		#print keycode
		controlDown = event.CmdDown()
		#print 'grid ctrl: ',controlDown
		if controlDown and keycode == 65:
			print "Ctrl-A grid"
			#self.page.SetSelection(-1, -1)
			self.SelectAll()
		#if keycode==344: #F5 
		#	self.ExecSQL()
		
		if controlDown and keycode == 67:
			print "grid Ctrl-C"		
			if self.GetSelectedCells():
				print "Selected cells " + str(self.GetSelectedCells())
			 # If selection is block...
			if self.GetSelectionBlockTopLeft():
				print "Selection block top left " + str(self.GetSelectionBlockTopLeft())
			if self.GetSelectionBlockBottomRight():
				print "Selection block bottom right " + str(self.GetSelectionBlockBottomRight())
			
			# If selection is col...
			if self.GetSelectedCols():
				print "Selected cols " + str(self.GetSelectedCols())
			
			# If selection is row...
			if self.GetSelectedRows():
				print "Selected rows " + str(self.GetSelectedRows())
			self.copy()
		print keycode
		if keycode==344: #F5 			
			assert self.surrent_sql, 'Re-exec sql is not set'
			assert self.connect_as, 'Re-exec db is not set'
			send( "re_exec_sql", (self.surrent_sql,self.connect_as) )

		event.Skip()	

		
	def copy(self):
		print "Copy method"
		# Number of rows and cols
		# data variable contain text that must be set in the clipboard
		
		data = ''
		#print(dir(self))

		
		if self.GetSelectionBlockTopLeft() and self.GetSelectionBlockBottomRight():
			#print "copy blocks %s , %s" % (self.GetSelectionBlockTopLeft(), self.GetSelectionBlockBottomRight())
			#rows = self.GetSelectionBlockBottomRight()[0][0] - self.GetSelectionBlockTopLeft()[0][0] + 1
			#cols = self.GetSelectionBlockBottomRight()[0][1] - self.GetSelectionBlockTopLeft()[0][1] + 1
			rows_from = []
			rows_to = []
			for r in self.GetSelectionBlockTopLeft():
				rows_from.append(r[0])
			for r in self.GetSelectionBlockBottomRight():
				rows_to.append(r[0])
			cols = []
			for c in range(len(self.GetSelectionBlockTopLeft())):
				cols.append(range(self.GetSelectionBlockTopLeft()[c][1],self.GetSelectionBlockBottomRight()[c][1]+1))
			#print rows_from,rows_to, cols
			#sys.exit(1)
			
			#set([1,2]).union(set([2,3]))
			data=''
			for colset in cols:
				#print self.GetColLabelValue(i)
				for c in colset:
					data = data+self.GetColLabelValue(c) + '\t'	
			data = data + '\n'	
			#print 			self.GetColLabelValue([0,1])
			#print data
			#sys.exit(1)
			# For each cell in selected range append the cell value in the data variable
			# Tabs '\t' for cols and '\r' for rows
			for r in range(min(rows_from),max(rows_to)):
				#print 'r=',r
				for cs in range(len(cols)):
					#print 'cs=', cs
					for c in range(len(cols[cs])):	
						#print c, cols[cs][c]
						if r>=rows_from[cs] and r<=rows_to[cs]:
							#print r, 'value= ',self.GetCellValue(r, cols[cs][c])
							data = data + str(self.GetCellValue(r, cols[cs][c]))
						#else:
						#	data = data + '\t'
						#data = data + str(self.GetCellValue(self.GetSelectionBlockTopLeft()[0][0] + r, self.GetSelectionBlockTopLeft()[0][1] + c))
						if c < len(cols[cs]) - 1:						
							data = data + '\t'
					if cs < len(cols) - 1:						
						data = data + '\t'
					#print '\n'
				data = data + '\n'
			#print data
		if self.GetSelectedCols():
			rows=self.GetNumberRows()
			cols =len(self.GetSelectedCols())
			for c in range(cols):
				#print self.GetColLabelValue(i)
				data = data+self.GetColLabelValue(self.GetSelectedCols()[0]+c) + '\t'	
			data = data + '\n'
			print "copy cols %s " % self.GetSelectedCols()
			#pprint (self.GetNumberRows())
			print cols			
			for r in range(rows):
				for c in range(cols):
					data = data + str(self.GetCellValue(r, self.GetSelectedCols()[0]+c))
					if c < cols - 1:
						data = data + '\t'
				data = data + '\n'	
		if self.GetSelectedRows():
			rows=len(self.GetSelectedRows())
			cols =self.GetNumberCols()	
			for c in range(cols):
				#print self.GetColLabelValue(i)
				data = data+self.GetColLabelValue(c) + '\t'
			data = data + '\n'

			print "copy rows, cols  %s %s"  %  (rows,cols)			
			#sys.exit(1)
			#pprint (self.GetNumberRows())
			print cols			
			for r in range(rows):
				for c in range(cols):
					data = data + str(self.GetCellValue(self.GetSelectedRows()[0]+r, c))
					if c < cols - 1:
						data = data + '\t'
				data = data + '\n'	
		if self.GetSelectedCells():
			data=str(self.GetSelectedCells())
		if not data:
			row = self.GetGridCursorRow()
			col = self.GetGridCursorCol()

			data = self.GetCellValue(row, col)
			
		# Create text data object
		clipboard = wx.TextDataObject()
		# Set data object value
		clipboard.SetText(data)
		# Put the data in the clipboard
		if wx.TheClipboard.Open():
			wx.TheClipboard.SetData(clipboard)
			wx.TheClipboard.Close()
		else:
			wx.MessageBox("Can't open the clipboard", "Error")		

	def copy0(self):
		print "Copy method"
		# Number of rows and cols
		# data variable contain text that must be set in the clipboard
		
		data = ''
		#print(dir(self))

		
		if self.GetSelectionBlockTopLeft() and self.GetSelectionBlockBottomRight():
			print "copy blocks %s %s" % (self.GetSelectionBlockTopLeft(), self.GetSelectionBlockBottomRight())
			rows = self.GetSelectionBlockBottomRight()[0][0] - self.GetSelectionBlockTopLeft()[0][0] + 1
			cols = self.GetSelectionBlockBottomRight()[0][1] - self.GetSelectionBlockTopLeft()[0][1] + 1
			print rows, cols
			for c in range(cols):
				#print self.GetColLabelValue(i)
				data = data+self.GetColLabelValue(self.GetSelectionBlockTopLeft()[0][1]+c) + '\t'	
			data = data + '\n'			

			# For each cell in selected range append the cell value in the data variable
			# Tabs '\t' for cols and '\r' for rows
			for r in range(rows):
				print r
				for c in range(cols):
					print c
					data = data + str(self.GetCellValue(self.GetSelectionBlockTopLeft()[0][0] + r, self.GetSelectionBlockTopLeft()[0][1] + c))
					if c < cols - 1:
						
						data = data + '\t'
				data = data + '\n'
			
		if self.GetSelectedCols():

			rows=self.GetNumberRows()
			cols =len(self.GetSelectedCols())
			for c in range(cols):
				#print self.GetColLabelValue(i)
				data = data+self.GetColLabelValue(self.GetSelectedCols()[0]+c) + '\t'	
			data = data + '\n'
			print "copy cols %s " % self.GetSelectedCols()
			#pprint (self.GetNumberRows())
			print cols			
			for r in range(rows):
				for c in range(cols):
					data = data + str(self.GetCellValue(r, self.GetSelectedCols()[0]+c))
					if c < cols - 1:
						data = data + '\t'
				data = data + '\n'	
		if self.GetSelectedRows():
			rows=len(self.GetSelectedRows())
			cols =self.GetNumberCols()	
			for c in range(cols):
				#print self.GetColLabelValue(i)
				data = data+self.GetColLabelValue(c) + '\t'
			data = data + '\n'

			print "copy rows, cols  %s %s"  %  (rows,cols)			
			#sys.exit(1)
			#pprint (self.GetNumberRows())
			print cols			
			for r in range(rows):
				for c in range(cols):
					data = data + str(self.GetCellValue(self.GetSelectedRows()[0]+r, c))
					if c < cols - 1:
						data = data + '\t'
				data = data + '\n'	
			
		# Create text data object
		clipboard = wx.TextDataObject()
		# Set data object value
		clipboard.SetText(data)
		# Put the data in the clipboard
		if wx.TheClipboard.Open():
			wx.TheClipboard.SetData(clipboard)
			wx.TheClipboard.Close()
		else:
			wx.MessageBox("Can't open the clipboard", "Error")	
			
text = """\
select * from CUBE_DATA_20130702173203_ab LIMIT 15;"""
d=None

class QueryPanel(wx.Panel):
	"""
	This will be the first notebook tab
	"""
	#----------------------------------------------------------------------
	def __init__(self, parent,ignore_change=False):
		""""""

		wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

		sizer = wx.BoxSizer(wx.VERTICAL)
		#txtOne = wx.TextCtrl(self, wx.ID_ANY, "")
		#txtTwo = wx.TextCtrl(self, wx.ID_ANY, "")

		
		b = wx.Button(self, 10, "Execute")
		self.Bind(wx.EVT_BUTTON, self.OnClick, b)
		b.SetDefault()
		b.SetSize(b.GetBestSize())
		self.parent=parent

		dbs = ['MRR_BI', 'MRR', 'MRR_STG','MRR_ARC']
		users = ['MRR_ETL_USER']
		self.connect_db=wx.ComboBox(self, 0,   choices=dbs, style=wx.CB_READONLY)
		self.connect_db.SetValue('MRR_BI')
		self.connect_user=wx.ComboBox(self, 0,   choices=users, style=wx.CB_READONLY)
		self.connect_user.SetValue('MRR_ETL_USER')
		
		bsizer = wx.BoxSizer(wx.HORIZONTAL)
		bsizer.Add(self.connect_db, 0, wx.LEFT)
		bsizer.Add(self.connect_user, 1, wx.LEFT)
		bsizer.Add(b, 1, wx.LEFT)

		
		sizer = wx.BoxSizer(wx.VERTICAL)
		#sizer.Add(txtOne, 0, wx.ALL, 5)
		#sizer.Add(txtTwo, 0, wx.ALL, 5)
		sizer.Add(bsizer, 0, wx.ALL, 3)
		print 'qp parent id=', parent.Id
		self.editor = CodeEditor(self, abs(parent.Id),True)
		#self.editor.ignore_change=ignore_change
		self.page = self.onWidgetSetup(self.editor,
								 wx.EVT_KEY_DOWN, self.onTextKeyEvent,
								 sizer)
		print 'In init:',self.page.changed,self.editor.ignore_change
		#font1 = wx.Font(12, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Consolas')
		#self.page.SetFont(font1)

		#self.page.SetDimensions(x=150, y=60, width=100, height=20)
		
		#sizer.Add(self.page,  1, wx.EXPAND)
		#sizer.Add(nb,  1, wx.EXPAND)
		
		
		self.SetSizer(sizer)
	def NoticeChange(self):
		self.editor.ignore_change=False		
	def UnChange(self):
		print 'unchanging qp'
		self.editor.changed=False
	def InitTextValue(self, value):
		print 'Before text init: ', self.page.changed
		self.page.SetValue(value)
		self.page.changed=False
		
	def db(self):
		return self.connect_db.GetValue()
	def user(self):
		return self.connect_user.GetValue()		
	def connect_as(self):
		return (self.db(), self.user())	
		
	def onWidgetSetup(self, widget, event, handler, sizer):
		widget.Bind(event, handler)
		#sizer.Add(widget, 0, wx.ALL, 5)
		sizer.Add(widget,  1, wx.EXPAND)
		return widget
	def onTextKeyEvent(self, event):
		print  'Editor changed: ', self.editor.changed
		keycode = event.GetKeyCode()
		print keycode
		controlDown = event.CmdDown()
		print 'ctrl: ',controlDown
		if controlDown and keycode == 65:
			print "Ctrl-A"
			self.page.SetSelection(-1, -1)
		#if controlDown and keycode == 83:
		#	print "Ctrl-S"
		#	wx.PyCommandEvent(wx.ID_SAVE, self.GetId())
		#	self.GetEventHandler().ProcessEvent(event)
			
		if keycode==344: #F5 
			sql=self.getSQL()			
			self.ExecSQL(sql,self.connect_as())
		if keycode==343: #F4 
			on = self.getTableName()
			print 'getTableName: ', on
			#m = re.match('((?P<db>[\w\_]+)?\.?(?P<owner>[\w\_]+)?\.)?(?P<tn>[\w\_]+)',on)
			m = re.match('(((?P<db>[\w\_]+)\.)?(((?P<owner>[\w\_]+)\.)|\.))?(?P<tn>[\w\_]+)$',on)
			db=owner=tn=None
			print db,owner,tn
			#if len(on)
			print m
			gd=()
			if m:
				gd = m.groupdict()
				#print gd
				#print gd.values()
				(owner,tn,db) = gd.values()
				print gd
				"""if gd.has_key('tn'):
					tn= gd['tn']
				if gd.has_key('db'):
					db= gd['db']	
				if gd.has_key('owner'):
					owner= gd['owner']						
				print gd
				pprint(dir(m))"""
			assert tn, 'Table name is not defined'
			#sys.exit(1)
			assert gd, 'Object is not set.'
			#global ddb, duser
			#(owner,tn,db)= gd.values()
			#if not db: db=ddb
			#if not owner: owner=duser	
			#obj=(owner,tn,db)	
			obj=gd.values()			
			(info, r_owner, r_db, if_exists)= self.getTableInfo(obj)
			(owner,tn,db)=obj
			if not db: db=r_db
			#if not owner: owner=r_owner
			#print desc
			#sys.exit(1)
			if if_exists:
				(status, err, rowcount,headers,desc)= self.getTableDDL((owner,tn,db, r_owner))
			else:
				(status, err, rowcount,headers,desc)=(0,'Table does not exists',0,[1],'Table does not exists')
			#sys.exit(1)	
			
			self.DescribeTable((status, err, rowcount,headers,"%s\n%s" % (info,desc)),(owner,tn,db, r_owner))
				
			
		if keycode==345: #F6 
			#global ddb
			db=self.db()
			sql=self.getSQL()
			#self.ExecSQL("EXPLAIN PLAN FOR %s" % sql)	
			self.ExplainSQL(sql,db)
						
		event.Skip()
	def getTableInfo(self, obj):
		#global ddb, duser
		(owner,tn,db)= obj
		s_owner="'%s'" % owner
		"""if not db: 
			db=ddb
			if not owner: 
				owner=duser
				s_owner="'%s'" % owner
		else:
			if not owner: 
				s_owner="owner" """
		if not db: db=self.db()
		if not owner or owner.upper()=='ADMIN': s_owner="owner"
		print s_owner,owner,tn,db
		#if _db: db=_db
		#if len(obj)==2:			
		sql="""
select OWNER,TABLENAME,   DATABASE
  from _v_table_xdb 
 where database= '%s' 
   and owner = %s 
   and tablename='%s' 
;
				""" % (db,s_owner,tn)
		#else: 
		#	if len(obj)==1:
		#		sql="select NAME, OWNER, TYPE, DATABASE, sum(attcolleng)  length from _v_relation_column where name='%s' group by NAME, OWNER, TYPE, DATABASE;" % tuple(obj)
		#	else:
		#		return 'Unsupported object type.'
		#sys.exit(1)		
		#sql="select NAME, OWNER, TYPE, DATABASE, sum(attcolleng)  length from _v_relation_column where name='%s' group by NAME, OWNER, TYPE, DATABASE;;" % tn
		(status, err, rowcount,headers, out)=query(sql, self.connect_as())
		print status, err, rowcount,headers
		print out
		
		desc="Table %s.%s doesn't exists in %s " % (owner,tn,db)
		if_exists=0
		r_owner=None
		if out:
			desc = "OWNER: %s; TABLE: %s;  DB: %s; \n" % out[0]
			if_exists=1
			r_owner=out[0][0]
		return (desc, r_owner,db, if_exists)
		
	def getTableDDL(self, obj):
		(owner,tn,db, r_owner)= obj
		assert db, 'Database owner is not set'
		assert r_owner, 'Table real owner is not set'
		assert tn, 'Table name is not set'
		print owner,tn,db
		
		sql="""
select ATTNAME,FORMAT_TYPE, decode(zmapped,TRUE, '--zmapped','') zmapped  
  from _v_relation_column 
 where database= '%s' 
   and owner = '%s'
   and name='%s' 
 order by attnum;
 """ %  (db, r_owner,tn)
		
		(status, err, rowcount,headers, out)=query(sql,(db,self.user()))
		
		ddl='\nCREATE TABLE %s (' % '.'.join((db,r_owner,tn))
		zmapped=''
		ml=[0,0]
		clist=''
		#define max length of the columns
		for r in out:
			for i in range(0,2):
				ml[i]=max(ml[i],len(r[i]))
		print ml
		for r in out:
			#ddl ="%s\n%s" (ddl,"")
			#print r
			zmapped=''
			ddl = "%s\n%s" % (ddl,"  %s\t%s,\t%s" % (r[0].ljust(ml[0],' '),r[1].ljust(ml[1],' '),r[2]))
			zmapped=r[2]
			clist='%s, %s' % (clist, r[0])
		#print ddl
		#print zmapped
		desc ="%s\t%s\n);\n\n" % (ddl.strip(',\t%s' % zmapped), zmapped)	 
		# get distibution columns
		desc ="%s\n\nselect * from _V_TABLE_DIST_MAP where tablename='%s'" %(desc,tn)
		# get organize columns
		desc ="%s\n\nselect * from _V_TABLE_ORGANIZE_COLUMN where tablename='%s'" %(desc,tn)
		# add count (*)
		desc ="""%s\n\nCreate or replace materialized view %s.%s.MV_%s as
select GRAIN_ID from %s.%s.%s
order by GRAIN_ID;
GENERATE STATISTICS ON %s.%s.%s;""" % (desc,db,r_owner,tn, db,r_owner,tn,db,r_owner,tn)
		# add count (*)
		desc ="%s\n\nSELECT count(*) \n  FROM %s.%s.%s;" % (desc,db,r_owner,tn)
		# data skew
		desc ='%s\n\nselect distinct datasliceid, count(*) over (partition by datasliceid) from %s.%s.%s'  % (desc,db,r_owner,tn)
		# gen stats
		desc ='%s\n\nGENERATE STATISTICS ON %s.%s.%s'  % (desc,db,r_owner,tn)
		#list all MVs
		desc ="%s\n\nselect * from _V_SPMVIEW where basename='%s'"  % (desc,tn)
		#refresh all MVs
		desc ="%s\n\nALTER VIEWS ON %s.%s.%s MATERIALIZE REFRESH;"  % (desc,db,r_owner,tn)
		";"
		#list of all MV definitions
		desc ="%s\n\nselect 'CREATE VIEW '||viewname||' AS '|| definition from _V_VIEW where upper(viewname) in (select upper(viewname) from _V_SPMVIEW where basename='%s')"  % (desc,tn)		
		# add SELECT ALL
		desc = "%s\n\nSELECT %s \n  FROM %s.%s.%s;" % (desc,clist.strip(','),db,r_owner,tn)
		# get distibution columns
		desc ="%s\n\nselect * from _V_TABLE_DIST_MAP where tablename='%s'" %(desc,tn)
		# table size
		desc ="""%s\n
select objname, sum(used_bytes)/1024 size_in_KB,  sum(used_bytes)/1024/1024 size_in_MB,  sum(used_bytes)/1024/1024/1024 size_in_GB
from _V_OBJ_RELATION_XDB 
join _V_SYS_OBJECT_DSLICE_INFO on (objid = tblid) 
where objname = '%s'
group by objname\n""" %(desc,tn)
		return (status, err, rowcount,headers,desc )
		#sys.exit(1)


	def DescribeTable(self, d, obj):
		#global ddb, duser
		(owner,tn,db, r_owner)= obj
		if not db: db=self.db()
		td="%s" % tn
		
		if owner: td="%s.%s" % (owner,tn)	
		else:
			if r_owner:	td="%s.%s" % (r_owner,tn)
			
		start_time = time.time()
		(status, err, rowcount, headers, desc)=d
		print 'out= %s,%s,%s,%s ' % (status, err, rowcount, headers)
		if status and err:
			self.parent.rp.pages[1][0].Error(err)
			self.SetFocus()
			#self.parent.rp.pages[1][0].SetFocus()
		else: 	
			if not status and headers:
				if rowcount>0:
					if 1:
						print 'posting'
						send( "add_describe", (td,desc) )
						#evt = SomeNewEvent(attr1="hello", attr2=654)
						#post the event
						#wx.PostEvent(self.wxObject, evt)
						#print self.parent.parent.__name__ #rp.pages[1][0].Status(desc)
						#self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
						#self.parent.rp.pages[1][0].SetFocus()
					else:
						self.parent.rp.pages[1][0].Status(desc)
						self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
						self.parent.rp.pages[1][0].SetFocus()
						#self.SetFocus()
				else:
					self.parent.rp.pages[1][0].Error('Table %s does not exists in %s.\n'  % (td,db))
					self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
					self.parent.rp.pages[1][0].SetFocus()
					self.SetFocus()
			else:
				if status>0 and not headers:
					self.parent.rp.pages[1][0].Status('%d rows affected.' % status)
					self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
					self.parent.rp.pages[1][0].SetFocus()	
					self.SetFocus()
				else:
					if status==-1 and not headers and not rowcount:
						self.parent.rp.pages[1][0].Error('Cannot DROP/TRUNCATE in describe')
						self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
						self.parent.rp.pages[0][0].SetFocus()
						self.SetFocus()
					if status==0 and not headers and not rowcount:
						self.parent.rp.pages[1][0].Error('Cannot CREATE in describe.')
						self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
						self.parent.rp.pages[0][0].SetFocus()	
						self.SetFocus()	
						
	def getTableName(self):
		sys.stdout.write(self.page.GetText())
		start, end = self.page.GetSelection()
		print '#'*40
		print '\nSelection:-------', start, end,(end-start)
		#if wx.Platform == "__WXMSW__":  # This is why GetStringSelection was added
		#	#self.page.SetValue(self.page.GetValue().replace('\n', '\r\n')) 
		text = self.page.GetText()
		#if wx.Platform == "__WXMSW__":  # This is why GetStringSelection was added
		#	text = text.replace('\n', '\r\n')	
				
		if abs(end-start)>0:
			if end<start:
				end, start=start, end
			sql=text[start:end]
			print 'selection: ', sql
			return sql.upper().strip().replace('"','').replace(';','').replace(')','')
		else:
			

			ip = self.page.GetCurrentPos() #GetInsertionPoint()
			lp = self.page.GetLastPosition()
			print "Coordinates: ",ip, lp
			#sys.exit(1)
			before=text[:ip] #.rstrip(" ")

			print ">%s<" % before
			after=text[ip:]
			print after
			for m in re.finditer('(\s+)', before):
				
				print '%02d-%02d: %s' % (m.start(), m.end(), m.group(0))
				last=m
			last = list(re.finditer('(\s+)', before))[-1:]
			print last
			(q_start, q_end) = (-1,-1)
			if len(last)==1:
				#last = last2[0]
				(ignore, q_start, white) = (last[0].start(), last[0].end(), last[0].group(0))
				print q_start
			
			sql=text
			m =list(re.finditer('(\s+)', after))
			if m:
				#last = last2[0]
				(q_end, ignore, white) = (m[0].start(), m[0].end(), m[0].group(0))
				print q_end, ignore, white
			
			(q_from, q_to) = (q_start,len(before)+q_end)
			if q_end==-1:
				(q_from, q_to) = (q_start,lp)
				sql=text[q_start:lp]
			if q_start==-1:
				(q_from, q_to) = (0,len(before)+q_end)
				sql=text[0:len(before)+q_end]
			
			
			if q_start==-1 and q_end==-1:
				print "resetting..."
				q_from, q_to = (-1, -1)
				sql=text
				
			print "cuts: ", q_start, q_end
			print "highlighting: ", q_from, q_to	
			self.page.SetSelection(q_from, q_to)
			if q_from>0 and q_to>0:
				sql=text[q_from:q_to]
			return sql.upper().strip().replace('"','').replace(';','').replace(')','')
		
	def OnClick(self, event):
		#msg = 'Retrieving data...'
		#title = 'NZ SQL'
		
		self.ExecSQL(self.getSQL(), self.connect_as());
		#del d
	def getSQL(self):
		sys.stdout.write(self.page.GetText())
		start, end = self.page.GetSelection()
		print '#'*40
		print '\nSelection:-------', start, end,(end-start)
		#if wx.Platform == "__WXMSW__":  # This is why GetStringSelection was added
		#	#self.page.SetValue(self.page.GetValue().replace('\n', '\r\n')) 
		text = self.page.GetText()
		#if wx.Platform == "__WXMSW__":  # This is why GetStringSelection was added
		#	text = text.replace('\n', '\r\n')	
				
		if abs(end-start)>0:
			if end<start:
				end, start=start, end
			sql=text[start:end]
			print 'selection: ', sql
		else:
			

			ip = self.page.GetCurrentPos() #GetInsertionPoint()
			lp = self.page.GetLastPosition()
			print "Coordinates: ",ip, lp
			#sys.exit(1)
			before=text[:ip] #.rstrip(" ")

			print ">%s<" % before
			after=text[ip:]
			print after
			for m in re.finditer('\n(\s+)?\n', before):
				
				print '%02d-%02d: %s' % (m.start(), m.end(), m.group(0))
				last=m
			last = list(re.finditer('\n(\s+)?\n', before))[-1:]
			print last
			(q_start, q_end) = (-1,-1)
			if len(last)==1:
				#last = last2[0]
				(ignore, q_start, white) = (last[0].start(), last[0].end(), last[0].group(0))
				print q_start
			
			sql=text
			m =list(re.finditer('\n(\s+)?\n', after))
			if m:
				#last = last2[0]
				(q_end, ignore, white) = (m[0].start(), m[0].end(), m[0].group(0))
				print q_end, ignore, white
			
			(q_from, q_to) = (q_start,len(before)+q_end)
			if q_end==-1:
				(q_from, q_to) = (q_start,lp)
				sql=text[q_start:lp]
			if q_start==-1:
				(q_from, q_to) = (0,len(before)+q_end)
				sql=text[0:len(before)+q_end]
			
			
			if q_start==-1 and q_end==-1:
				print "resetting..."
				q_from, q_to = (-1, -1)
				sql=text
				
			print "cuts: ", q_start, q_end
			print "highlighting: ", q_from, q_to	
			self.page.SetSelection(q_from, q_to)
			if q_from>0 and q_to>0:
				sql=text[q_from:q_to]
			#return sql
		return sql

	def ExecSQL(self, sql, connect_as=None):
		assert sql, 'sql statement is not defined'
		if not connect_as:
			connect_as=self.connect_as()
		self.parent.rp.sql=sql
		self.parent.rp.db=connect_as
		start_time = time.time()
		(status, err, rowcount, headers)=self.parent.rp.pages[0][0].grid.UpdateLimitedGrid(sql,connect_as)
		print 'out= %s,%s,%s,%s ' % (status, err, rowcount, headers)
		if status and err: 
			self.parent.rp.pages[1][0].Error(err)
			#self.parent.rp.pages[1][0].SetFocus()
			self.SetFocus()
		else: 	
			if not status and headers:
				if rowcount>0:
					self.parent.rp.pages[1][0].Status('%d rows returned.' % rowcount)
					self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
					self.parent.rp.pages[0][0].SetFocus()
					self.SetFocus()
				else:
					self.parent.rp.pages[1][0].Status(err)
					self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
					self.parent.rp.pages[1][0].SetFocus()
					self.SetFocus()
			else:
				if status>0 and not headers:
					self.parent.rp.pages[1][0].Status('%d rows affected.' % status)
					self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
					self.parent.rp.pages[1][0].SetFocus()	
					self.SetFocus()
				else:
					if status==-1 and not headers and not rowcount:
						self.parent.rp.pages[1][0].Status('DROP/TRUNCATE success.')
						self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
						self.parent.rp.pages[1][0].SetFocus()
						self.SetFocus()
					if status==0 and not headers and not rowcount:
						self.parent.rp.pages[1][0].Status('CREATE success.')
						self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
						self.parent.rp.pages[1][0].SetFocus()	
						self.SetFocus()	
						
		
					
				
		#print status, err
	def ExplainSQL(self,sql,db):
		sql=self.getSQL()
		start_time = time.time()
		(status, err, rowcount,headers, out)=query("EXPLAIN PLAN FOR %s" % sql, self.connect_as())
		print 'out= %s,%s,%s,%s ' % (status, err, rowcount, headers)
		#pprint(out[0])
		exp=''
		for o in out: exp="%s\n%s" % (exp,''.join(o))
		if status and err: 
			self.parent.rp.pages[1][0].Error(err)
			#self.parent.rp.pages[1][0].SetFocus()
			self.SetFocus()
		else: 	
			if not status and headers:
				if rowcount>0:
					self.parent.rp.pages[1][0].Status('%d rows returned during explain.' % rowcount)
					self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
					#self.parent.rp.pages[0][0].SetFocus()
					#self.SetFocus()
					send( "add_explain_sql", ('explain',sql,db,exp) )
				else:
					self.parent.rp.pages[1][0].Status(err)
					self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
					self.parent.rp.pages[1][0].SetFocus()
					self.SetFocus()
			else:
				if status>0 and not headers:
					self.parent.rp.pages[1][0].Status('%d rows affected.' % status)
					self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
					self.parent.rp.pages[1][0].SetFocus()	
					self.SetFocus()
				else:
					if status==-1 and not headers and not rowcount:
						self.parent.rp.pages[1][0].Status('DROP/TRUNCATE success.')
						self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
						self.parent.rp.pages[1][0].SetFocus()
						self.SetFocus()
					if status==0 and not headers and not rowcount:
						self.parent.rp.pages[1][0].Status('CREATE success.')
						self.parent.rp.pages[1][0].Elapsed(time.time() - start_time)			
						self.parent.rp.pages[1][0].SetFocus()	
						self.SetFocus()				
					
				
		#print status, err
		
#----------------------------------------------------------------------
class ResultsPanel(wx.Panel):
	"""
	This will be the first notebook tab
	"""
	#----------------------------------------------------------------------
	def __init__(self, parent):
		""""""

		wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

		sizer = wx.BoxSizer(wx.VERTICAL)
		#txtOne = wx.TextCtrl(self, wx.ID_ANY, "")
		#txtTwo = wx.TextCtrl(self, wx.ID_ANY, "")
		#page = wx.TextCtrl(self, -1, text, style=wx.TE_MULTILINE)
		#nb = wx.aui.AuiNotebook(self)
		self.grid = SimpleGrid(self, sys.stdout)
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		#sizer.Add(txtOne, 0, wx.ALL, 5)
		#sizer.Add(txtTwo, 0, wx.ALL, 5)
		sizer.Add(self.grid,  -1, wx.EXPAND)
		#sizer.Add(nb,  1, wx.EXPAND)
		self.SetSizer(sizer)
		self.sql=''
		self.db=''
		
	def onTextKeyEvent(self, event):
		keycode = event.GetKeyCode()
		print keycode
		controlDown = event.CmdDown()
		print 'res ctrl: ',controlDown
		if controlDown and keycode == 65:
			print "res Ctrl-A"
			#self.page.SetSelection(-1, -1)
		if keycode==344: #F5 
			assert sql, 'Re-exec sql is not set'
			assert db, 'Re-exec db is not set'
			send( "re_exec_sql", (sql,db) )
		event.Skip()
#----------------------------------------------------------------------
class OutputPanel(wx.Panel):
	"""
	SQL exucution status messages
	"""
	#----------------------------------------------------------------------
	def __init__(self, parent):
		""""""

		wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

		sizer = wx.BoxSizer(wx.VERTICAL)
		#txtOne = wx.TextCtrl(self, wx.ID_ANY, "")
		#txtTwo = wx.TextCtrl(self, wx.ID_ANY, "")
		#page = wx.TextCtrl(self, -1, text, style=wx.TE_MULTILINE)
		#nb = wx.aui.AuiNotebook(self)
		#self.grid = SimpleGrid(self, sys.stdout)
		#l4 = wx.StaticText(self, -1, "Rich Text")
		#pprint(dir(time))
		self.status = wx.TextCtrl(self, -1, str(datetime.datetime.now()),
							wx.DefaultPosition, wx.Size(50,300),
							wx.NO_BORDER | wx.TE_MULTILINE|wx.TE_RICH2)
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		#sizer.Add(txtOne, 0, wx.ALL, 5)
		#sizer.Add(txtTwo, 0, wx.ALL, 5)
		sizer.Add(self.status,  -1, wx.EXPAND)
		#sizer.Add(nb,  1, wx.EXPAND)
		self.SetSizer(sizer)
	def Error(self,err):
		#print(dir(self.status))
		self.status.SetValue(str(err))
		self.status.SetInsertionPoint(0)
		points = self.status.GetFont().GetPointSize() 
		style = self.status.GetFont().GetStyle()
		weight= self.status.GetFont().GetWeight()
		f = wx.Font(points+3,wx.FONTFAMILY_DEFAULT,style,weight)
		self.status.SetStyle(6, len(str(err)), wx.TextAttr("RED", wx.NullColour,f))
		 # get the current size
		#f = wx.Font(points, wx.ROMAN, None, wx.BOLD, True)
		#self.status.SetStyle(0, 5, wx.TextAttr("BLUE", wx.NullColour, f))
		self.SetFocus()
	def Status(self,status):
		#print(dir(self.status))
		self.status.SetValue("%s" % (str(status)))
		#self.status.SetInsertionPoint(0)
		#points = self.status.GetFont().GetPointSize() 
		#style = self.status.GetFont().GetStyle()
		#weight= self.status.GetFont().GetWeight()
		#f = wx.Font(points+3,wx.FONTFAMILY_DEFAULT,style,weight)
		#self.status.SetStyle(0, len(str(status)), wx.TextAttr("GREEN", wx.NullColour,f))
		 # get the current size
		#f = wx.Font(points, wx.ROMAN, None, wx.BOLD, True)
		#self.status.SetStyle(0, 5, wx.TextAttr("BLUE", wx.NullColour, f))
		self.SetFocus()
		
	def Elapsed(self,delta):
		#print(dir(self.status))
		
		self.status.SetValue("%s\nElapsed: %s seconds." % (self.status.GetValue(),delta))
	
		

#----------------------------------------------------------------------
class ExportPanel(wx.Panel):
	"""
	This will be the first notebook tab
	"""
	#----------------------------------------------------------------------
	def __init__(self, parent):
		""""""

		wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

		sizer = wx.BoxSizer(wx.VERTICAL)
		#txtOne = wx.TextCtrl(self, wx.ID_ANY, "")
		#txtTwo = wx.TextCtrl(self, wx.ID_ANY, "")
		#page = wx.TextCtrl(self, -1, text, style=wx.TE_MULTILINE)
		#nb = wx.aui.AuiNotebook(self)
		#self.grid = SimpleGrid(self, sys.stdout)
		text2 = wx.TextCtrl(self, -1, 'Export - sample text',
							wx.DefaultPosition, wx.Size(50,300),
							wx.NO_BORDER | wx.TE_MULTILINE)
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		#sizer.Add(txtOne, 0, wx.ALL, 5)
		#sizer.Add(txtTwo, 0, wx.ALL, 5)
		sizer.Add(text2,  -1, wx.EXPAND)
		#sizer.Add(nb,  1, wx.EXPAND)
		self.SetSizer(sizer)
		
class ResultsNbPanel(wx.Panel):
	"""
	This will be the first notebook tab
	"""
	#----------------------------------------------------------------------
	def __init__(self, parent):
		""""""
		wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

		# create the AuiNotebook instance
		nb = wx.aui.AuiNotebook(self)

		# add some pages to the notebook
		self.pages = [(ResultsPanel(nb), "Results"),
				 (OutputPanel(nb), "Output"),
				 (ExportPanel(nb), "Export")]
		for page, label in self.pages:
			nb.AddPage(page, label)

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(nb, 1, wx.EXPAND)
		self.SetSizer(sizer)
		
########################################################################
class TabPanel(wx.Panel):
	"""
	This will be the first notebook tab
	"""
	#----------------------------------------------------------------------
	def __init__(self, parent, ignore_change=False):
		""""""

		wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

		self._mgr = AUIManager(self)
		# create several text controls
		#text1 = wx.TextCtrl(self, -1, 'Pane 1 - sample text',
		#					wx.DefaultPosition, wx.Size(500,500),
		#					wx.NO_BORDER | wx.TE_MULTILINE)
		self.qp=QueryPanel(self, ignore_change)
		self.rp=ResultsNbPanel(self)
		self.parent=parent
		#text2 = wx.TextCtrl(self, -1, 'Pane 2 - sample text',
		#					wx.DefaultPosition, wx.Size(50,300),
		#					wx.NO_BORDER | wx.TE_MULTILINE)
		#self.grid = SimpleGrid(self, sys.stdout)
		#text3 = wx.TextCtrl(self, -1, 'Main content window',
		#					wx.DefaultPosition, wx.Size(50,100),
		#					wx.NO_BORDER | wx.TE_MULTILINE)
		
		# add the panes to the manager
		self._mgr.AddPane(self.qp, wx.CENTER)
		self._mgr.AddPane(self.rp, wx.CENTER)
		#self._mgr.AddPane(text3, wx.CENTER)

		# tell the manager to 'commit' all the changes just made
		self._mgr.Update()
	def OnMaximize(self, evt):
		info = self.mgr.GetPane("Notebook")
		if info.IsMaximized():
			self.mgr.RestorePane(info)
		else:
			self.mgr.RestoreMaximizedPane()
			self.mgr.MaximizePane(info)
		self.mgr.Update()		
	def UnChange(self):
		print 'unchanging tp'
		self.qp.UnChange()
	def NoticeChange(self):
		self.qp.NoticeChange()		

#import  wx
#import  wx.lib.newevent

import wx.lib.agw.aui as aui


#SomeNewEvent, EVT_SOME_NEW_EVENT = wx.lib.newevent.NewEvent()
#SomeNewCommandEvent, EVT_SOME_NEW_COMMAND_EVENT = wx.lib.newevent.NewCommandEvent()
from wx.lib.pubsub import pub


class SQLPanel(wx.Panel):
	"""
	This will be the first notebook tab
	"""
	#----------------------------------------------------------------------
	def __init__(self, parent, log):
		""""""
		wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

		# create the AuiNotebook instance
		self.nb = wx.aui.AuiNotebook(self)

		# add some pages to the notebook
		"""self.pages = [(TabPanel(self.nb), "SQL_1"),
				 (TabPanel(self.nb), "SQL_2"),
				 (TabPanel(self.nb), "SQL_3")]
		"""
		self.pages=[]
		self.new=0
		self.explain_cntr=0
		self.order=[]
		for p in range(3):
			self.AddNew("SQL_%d.sql" % p, text)
			self.new=p+1
			
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.nb, 1, wx.EXPAND)
		self.SetSizer(sizer)
		#self.bind_events()
		#self.Bind(EVT_SOME_NEW_EVENT, self.AddDescribe)
		#EVT_SOME_NEW_EVENT(self, self.AddDescribe)
		sub(self.AddDescribe, "add_describe")
		sub(self.AddExplainSQL, "add_explain_sql")
		self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CLOSED, self.onTabClose, self.nb)
		sub(self.reExecSQL, "re_exec_sql")
		sub(self.SetTextChanged2, "star_tab_name")

	def onTabClose(self, evt):
		print 'onTabClose'
		print self.order
		if self.order:
			last_selected=self.nb.GetPage(self.order.pop())
			last_selected.SetFocus()
		
	def AddDescribe(self, evt):
		(td,desc)=evt.data
		self.AddNew(td,desc)
	def AddExplainSQL(self, evt):
		(title,sql,db,exp)=evt.data
		self.AddNew(title,"--DB:\t%s\n%s\n\n%s" %(db,exp,sql))		

		
	def AddNew(self, label='', value='', ignore_change=False):
		if self.nb.PageCount:
			self.order.append(self.nb.GetSelection())

		print "on new2 ignore_change" , ignore_change
		if not label:
			label="SQL_%d.sql" % (len(self.pages)+1)	
		if label in ('explain'):
			label="EXPLAIN_%d.sql" % (self.explain_cntr+1)	
			self.explain_cntr +=1
		
		page = TabPanel(self.nb,ignore_change)
		#print(dir(page))
		print 'page.Id= ', page.Id
		page.file_name=label
		page.saved=False
		self.pages.append((page, label));
		#(page, label) = self.pages[-1:][0]
		#print page, label
		self.nb.AddPage(page, label)
		#page.qp.page.SetValue(value)
		print 'before' , page.qp.editor.ignore_change
		page.qp.InitTextValue(value) #.page.SetValue(value)
		print 'after' , page.qp.editor.ignore_change
		#self.SetFocus()
		print self.nb.PageCount
		selected_page = self.nb.GetPage(self.nb.PageCount-1)
		#print (dir(self.nb))
		self.nb.SetFocus()
		selected_page.SetFocus()
		print 'ending ' , page.qp.editor.ignore_change
		page.qp.editor.ignore_change=False

	def reExecSQL(self, evt):
		(sql, connect_as) = evt.data
		selected_num = self.nb.GetSelection()            
		selected = self.nb.GetPage(selected_num)
		#selected.qp.ExecSQL(sql, connect_as)
		selected.qp.ExecSQL(sql)
	def SetTextChanged2(self, evt):
		(ID) = evt.data
		
		print 'Change tabid=', ID
		selected_num = self.nb.GetSelection()            
		print selected_num
		selected = self.nb.GetPage(selected_num)
		print  '||||||SetTextChanged ', selected.qp.editor.changed,selected.qp.editor.ignore_change
		#print selected
		#print selected.file_name
		#print dir(selected)
		print 'self.changed= %s' % selected.qp.editor.changed
		print 'self.ignore_changed= %s' % selected.qp.editor.ignore_change
		self.nb.SetPageText(selected_num,"%s*" % selected.file_name)
		selected.qp.editor.ignore_change=False
		#selected.SetLabel("test" % selected.file_name)
		
########################################################################

_treeList = [
	# new stuff
	('Recent Additions/Updates', [
		'RichTextCtrl',
		'Treebook',
		'Toolbook',
		'BitmapFromBuffer',
		'RawBitmapAccess',
		'DragScroller',
		'DelayedResult',
		'ExpandoTextCtrl',
		'AboutBox',
		'AlphaDrawing',
		'GraphicsContext',
		'CollapsiblePane',
		'ComboCtrl',
		'OwnerDrawnComboBox',
		'BitmapComboBox',
		'I18N',
		'Img2PyArtProvider',
		'SearchCtrl',
		'SizedControls',
		'AUI_MDI',
		'TreeMixin',
		'AdjustChannels',
		'RendererNative',
		'PlateButton',
		'ResizeWidget',
		'Cairo',
		'Cairo_Snippets',
		'SystemSettings',
		'GridLabelRenderer',
		'ItemsPicker',
		]),

	# managed windows == things with a (optional) caption you can close
	('Frames and Dialogs', [
		'AUI_DockingWindowMgr',
		'AUI_MDI',
		'Dialog',
		'Frame',
		'MDIWindows',
		'MiniFrame',
		'Wizard',
		]),

	# the common dialogs
	('Common Dialogs', [
		'AboutBox',
		'ColourDialog',
		'DirDialog',
		'FileDialog',
		'FindReplaceDialog',
		'FontDialog',
		'MessageDialog',
		'MultiChoiceDialog',
		'PageSetupDialog',
		'PrintDialog',
		'ProgressDialog',
		'SingleChoiceDialog',
		'TextEntryDialog',
		]),

	# dialogs from libraries
	('More Dialogs', [
		'ImageBrowser',
		'ScrolledMessageDialog',
		]),

	# core controls
	('Core Windows/Controls', [
		'BitmapButton',
		'Button',
		'CheckBox',
		'CheckListBox',
		'Choice',
		'ComboBox',
		'Gauge',
		'Grid',
		'Grid_MegaExample',
		'GridLabelRenderer',
		'ListBox',
		'ListCtrl',
		'ListCtrl_virtual',
		'ListCtrl_edit',
		'Menu',
		'PopupMenu',
		'PopupWindow',
		'RadioBox',
		'RadioButton',
		'SashWindow',
		'ScrolledWindow',
		'SearchCtrl',        
		'Slider',
		'SpinButton',
		'SpinCtrl',
		'SplitterWindow',
		'StaticBitmap',
		'StaticBox',
		'StaticText',
		'StatusBar',
		'StockButtons',
		'TextCtrl',
		'ToggleButton',
		'ToolBar',
		'TreeCtrl',
		'Validator',
		]),
	
	('"Book" Controls', [
		'AUI_Notebook',
		'Choicebook',
		'FlatNotebook',
		'Listbook',
		'Notebook',
		'Toolbook',
		'Treebook',
		]),

	('Custom Controls', [
		'AnalogClock',
		'ColourSelect',
		'ComboTreeBox',
		'Editor',
		'GenericButtons',
		'GenericDirCtrl',
		'ItemsPicker',
		'LEDNumberCtrl',
		'MultiSash',
		'PlateButton',
		'PopupControl',
		'PyColourChooser',
		'TreeListCtrl',
	]),
	
	# controls coming from other libraries
	('More Windows/Controls', [
		'ActiveX_FlashWindow',
		'ActiveX_IEHtmlWindow',
		'ActiveX_PDFWindow',
		'BitmapComboBox',
		'Calendar',
		'CalendarCtrl',
		'CheckListCtrlMixin',
		'CollapsiblePane',
		'ComboCtrl',
		'ContextHelp',
		'DatePickerCtrl',
		'DynamicSashWindow',
		'EditableListBox',
		'ExpandoTextCtrl',
		'FancyText',
		'FileBrowseButton',
		'FloatBar',  
		'FloatCanvas',
		'HtmlWindow',
		'IntCtrl',
		'MVCTree',   
		'MaskedEditControls',
		'MaskedNumCtrl',
		'MediaCtrl',
		'MultiSplitterWindow',
		'OwnerDrawnComboBox',
		'Pickers',
		'PyCrust',
		'PyPlot',
		'PyShell',
		'ResizeWidget',
		'RichTextCtrl',
		'ScrolledPanel',
		'SplitTree',
		'StyledTextCtrl_1',
		'StyledTextCtrl_2',
		'TablePrint',
		'Throbber',
		'Ticker',
		'TimeCtrl',
		'TreeMixin',
		'VListBox',
		]),

	# How to lay out the controls in a frame/dialog
	('Window Layout', [
		'GridBagSizer',
		'LayoutAnchors',
		'LayoutConstraints',
		'Layoutf',
		'RowColSizer',
		'ScrolledPanel',
		'SizedControls',
		'Sizers',
		'XmlResource',
		'XmlResourceHandler',
		'XmlResourceSubclass',
		]),

	# ditto
	('Process and Events', [
		'DelayedResult',
		'EventManager',
		'KeyEvents',
		'Process',
		'PythonEvents',
		'Threads',
		'Timer',
		##'infoframe',    # needs better explanation and some fixing
		]),

	# Clipboard and DnD
	('Clipboard and DnD', [
		'CustomDragAndDrop',
		'DragAndDrop',
		'URLDragAndDrop',
		]),

	# Images
	('Using Images', [
		'AdjustChannels',
		'AlphaDrawing',
		'AnimateCtrl',
		'ArtProvider',
		'BitmapFromBuffer',
		'Cursor',
		'DragImage',
		'Image',
		'ImageAlpha',
		'ImageFromStream',
		'Img2PyArtProvider',
		'Mask',
		'RawBitmapAccess',
		'Throbber',
		]),

	# Other stuff
	('Miscellaneous', [
		'AlphaDrawing',
		'Cairo',
		'Cairo_Snippets',
		'ColourDB',
		##'DialogUnits',   # needs more explanations
		'DragScroller',
		'DrawXXXList',
		'FileHistory',
		'FontEnumerator',
		'GraphicsContext',
		'GLCanvas',
		'I18N',        
		'Joystick',
		'MimeTypesManager',
		'MouseGestures',
		'OGL',
		'PrintFramework',
		'PseudoDC',
		'RendererNative',
		'ShapedWindow',
		'Sound',
		'StandardPaths',
		'SystemSettings',
		'Unicode',
		]),


	('Check out the samples dir too', [
		]),

]
_demoPngs = ["overview", "recent", "frame", "dialog", "moredialog", "core",
			 "book", "customcontrol", "morecontrols", "layout", "process", "clipboard",
			 "images", "miscellaneous"]
USE_CUSTOMTREECTRL = False
ALLOW_AUI_FLOATING = False
DEFAULT_PERSPECTIVE = "Default Perspective"
ID_New = wx.NewId()
class Main(wx.Frame):
	def __init__(self, parent, log):
		wx.Frame.__init__(self, parent, -1, "SQL Editor for Oracle", size=(1040,800))
		self.panel = SQLPanel(self, log)
		self._mgr = AUIManager(self)
		self.finddata = wx.FindReplaceData()
		self.finddata.SetFlags(wx.FR_DOWN)
		#self.firstTime = True
		self.finddlg = None
		#self.create_menu_bar()
		#self.bind_events()
		self.BuildMenuBar()
	def bind_events(self):		
		#self.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)
		self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
		self.Bind(wx.EVT_MENU, self.OnSave, menuSave)
		self.Bind(wx.EVT_MENU, self.OnSaveAs, menuSaveAs)
		self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
		self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)		
		self.Bind(wx.EVT_MENU, self.on_new, id=ID_New) 
	def BuildMenuBar(self):

		# Make a File menu
		self.mainmenu = wx.MenuBar()
		menu = wx.Menu()
		item = menu.Append(-1, '&Redirect Output',
						   'Redirect print statements to a window',
						   wx.ITEM_CHECK)
		self.Bind(wx.EVT_MENU, self.OnToggleRedirect, item)
 		menuOpen = menu.Append(wx.ID_OPEN, "&Open"," Open a file to edit")
		menuSave = menu.Append(wx.ID_SAVE, "&Save\tCtrl-S"," Save file")
		menuSaveAs = menu.Append(wx.ID_SAVEAS, "&SaveAs\tCtrl-E"," Save As file")
		menu.Append(ID_New, "New SQL")	
		
		exitItem = wx.MenuItem(menu, -1, 'E&xit\tCtrl-Q', 'Get the heck outta here!')
		exitItem.SetBitmap(images.catalog['exit'].GetBitmap())
		menu.AppendItem(exitItem)
		self.Bind(wx.EVT_MENU, self.OnFileExit, exitItem)
		wx.App.SetMacExitMenuItemId(exitItem.GetId())
		self.mainmenu.Append(menu, '&File')


		# Make a Demo menu
		menu = wx.Menu()
		for indx, item in enumerate(_treeList[:-1]):
			menuItem = wx.MenuItem(menu, -1, item[0])
			submenu = wx.Menu()
			for childItem in item[1]:
				mi = submenu.Append(-1, childItem)
				self.Bind(wx.EVT_MENU, self.OnDemoMenu, mi)
			menuItem.SetBitmap(images.catalog[_demoPngs[indx+1]].GetBitmap())
			menuItem.SetSubMenu(submenu)
			menu.AppendItem(menuItem)
		self.mainmenu.Append(menu, '&Demo')

		# Make an Option menu
		# If we've turned off floatable panels then this menu is not needed
		if ALLOW_AUI_FLOATING:
			menu = wx.Menu()
			auiPerspectives = self.auiConfigurations.keys()
			auiPerspectives.sort()
			perspectivesMenu = wx.Menu()
			item = wx.MenuItem(perspectivesMenu, -1, DEFAULT_PERSPECTIVE, "Load startup default perspective", wx.ITEM_RADIO)
			self.Bind(wx.EVT_MENU, self.OnAUIPerspectives, item)
			perspectivesMenu.AppendItem(item)
			for indx, key in enumerate(auiPerspectives):
				if key == DEFAULT_PERSPECTIVE:
					continue
				item = wx.MenuItem(perspectivesMenu, -1, key, "Load user perspective %d"%indx, wx.ITEM_RADIO)
				perspectivesMenu.AppendItem(item)
				self.Bind(wx.EVT_MENU, self.OnAUIPerspectives, item)

			menu.AppendMenu(wx.ID_ANY, "&AUI Perspectives", perspectivesMenu)
			self.perspectives_menu = perspectivesMenu

			item = wx.MenuItem(menu, -1, 'Save Perspective', 'Save AUI perspective')
			item.SetBitmap(images.catalog['saveperspective'].GetBitmap())
			menu.AppendItem(item)
			self.Bind(wx.EVT_MENU, self.OnSavePerspective, item)

			item = wx.MenuItem(menu, -1, 'Delete Perspective', 'Delete AUI perspective')
			item.SetBitmap(images.catalog['deleteperspective'].GetBitmap())
			menu.AppendItem(item)
			self.Bind(wx.EVT_MENU, self.OnDeletePerspective, item)

			menu.AppendSeparator()

			item = wx.MenuItem(menu, -1, 'Restore Tree Expansion', 'Restore the initial tree expansion state')
			item.SetBitmap(images.catalog['expansion'].GetBitmap())
			menu.AppendItem(item)
			self.Bind(wx.EVT_MENU, self.OnTreeExpansion, item)

			self.mainmenu.Append(menu, '&Options')
		
		# Make a Help menu
		menu = wx.Menu()
		findItem = wx.MenuItem(menu, -1, '&Find\tCtrl-F', 'Find in the Demo Code')
		findItem.SetBitmap(images.catalog['find'].GetBitmap())
		if 'wxMac' not in wx.PlatformInfo:
			findNextItem = wx.MenuItem(menu, -1, 'Find &Next\tF3', 'Find Next')
		else:
			findNextItem = wx.MenuItem(menu, -1, 'Find &Next\tCtrl-G', 'Find Next')
		findNextItem.SetBitmap(images.catalog['findnext'].GetBitmap())
		menu.AppendItem(findItem)
		menu.AppendItem(findNextItem)
		menu.AppendSeparator()

		shellItem = wx.MenuItem(menu, -1, 'Open Py&Shell Window\tF8',
								'An interactive interpreter window with the demo app and frame objects in the namesapce')
		shellItem.SetBitmap(images.catalog['pyshell'].GetBitmap())
		menu.AppendItem(shellItem)
		inspToolItem = wx.MenuItem(menu, -1, 'Open &Widget Inspector\tF9',
								   'A tool that lets you browse the live widgets and sizers in an application')
		inspToolItem.SetBitmap(images.catalog['inspect'].GetBitmap())
		menu.AppendItem(inspToolItem)
		if 'wxMac' not in wx.PlatformInfo:
			menu.AppendSeparator()
		helpItem = menu.Append(-1, '&About wxPython Demo', 'wxPython RULES!!!')
		wx.App.SetMacAboutMenuItemId(helpItem.GetId())

		self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
		self.Bind(wx.EVT_MENU, self.OnSave, menuSave)
		saveId = wx.NewId()
		self.Bind(wx.EVT_MENU, self.OnSave, id=saveId)
		
		self.Bind(wx.EVT_MENU, self.OnSaveAs, menuSaveAs)
		self.Bind(wx.EVT_MENU, self.on_new, id=ID_New) 
		
		self.Bind(wx.EVT_MENU, self.OnOpenShellWindow, shellItem)
		self.Bind(wx.EVT_MENU, self.OnOpenWidgetInspector, inspToolItem)
		self.Bind(wx.EVT_MENU, self.OnHelpAbout, helpItem)
		self.Bind(wx.EVT_MENU, self.OnHelpFind,  findItem)
		self.Bind(wx.EVT_MENU, self.OnFindNext,  findNextItem)
		self.Bind(wx.EVT_FIND, self.OnFind)
		self.Bind(wx.EVT_FIND_NEXT, self.OnFind)
		self.Bind(wx.EVT_FIND_CLOSE, self.OnFindClose)
		self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateFindItems, findItem)
		self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateFindItems, findNextItem)
		self.mainmenu.Append(menu, '&Help')
		self.SetMenuBar(self.mainmenu)

		if False:
			# This is another way to set Accelerators, in addition to
			# using the '\t<key>' syntax in the menu items.
			aTable = wx.AcceleratorTable([(wx.ACCEL_ALT,  ord('X'), exitItem.GetId()),
										  (wx.ACCEL_CTRL, ord('H'), helpItem.GetId()),
										  (wx.ACCEL_CTRL, ord('F'), findItem.GetId()),
										  #(wx.ACCEL_CTRL,  ord('S'), saveId ),
										  (wx.ACCEL_NORMAL, wx.WXK_F3, findNextItem.GetId()),
										 #(wx.ACCEL_NORMAL, wx.WXK_F8, shellItem.GetId()),
										  ])
			self.SetAcceleratorTable(aTable)
	def OnUpdateFindItems(self, evt):
		evt.Enable(self.finddlg == None)			
	def create_menu_bar(self):
		# create menu
		mb = wx.MenuBar()
		file_menu = wx.Menu()
		

		file_menu = wx.Menu()
		menuOpen = file_menu.Append(wx.ID_OPEN, "&Open"," Open a file to edit")
		menuSave = file_menu.Append(wx.ID_SAVE, "&Save"," Save file")
		menuSaveAs = file_menu.Append(wx.ID_SAVEAS, "&SaveAs"," Save As file")
		file_menu.Append(ID_New, "New SQL")		
		menuAbout= file_menu.Append(wx.ID_ABOUT, "&About"," Information about this program")
		menuExit = file_menu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
		#menuFind = file_menu.Append(wx.ID_FIND, "&Find"," Find")
		findItem = wx.MenuItem(file_menu, -1, '&Find\tCtrl-F', 'Find in the Demo Code')
		findItem.SetBitmap(images.catalog['find'].GetBitmap())
		findNextItem = wx.MenuItem(file_menu, -1, 'Find &Next\tF3', 'Find Next')
		findNextItem.SetBitmap(images.catalog['findnext'].GetBitmap())
		file_menu.AppendItem(findItem)
		file_menu.AppendItem(findNextItem)
		randomId = wx.NewId()
		self.Bind(wx.EVT_MENU, self.OnSave, id=randomId)
		self.Bind(wx.EVT_MENU, self.OnSaveAs, id=randomId)
		#fnd  = wx.NewId()
		self.Bind(wx.EVT_MENU, self.OnFind, id=findItem.GetId() )
	
		helpItem = file_menu.Append(-1, '&About wxPython Demo', 'wxPython RULES!!!')
		wx.App.SetMacAboutMenuItemId(helpItem.GetId())
	
		mb.Append(file_menu, "&File")
		self.SetMenuBar(mb)
		self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
		self.Bind(wx.EVT_MENU, self.OnSave, menuSave)
		self.Bind(wx.EVT_MENU, self.OnSaveAs, menuSaveAs)
		self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
		self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
		self.Bind(wx.EVT_MENU, self.on_new, id=ID_New) 
		self.Bind(wx.EVT_MENU, self.OnHelpAbout, helpItem)
		self.Bind(wx.EVT_MENU, self.OnHelpFind,  findItem)
		self.Bind(wx.EVT_MENU, self.OnFindNext,  findNextItem)
		self.Bind(wx.EVT_FIND, self.OnFind)
		#self.Bind(wx.EVT_FIND_NEXT, self.OnFind)
		#self.Bind(wx.EVT_FIND_CLOSE, self.OnFindClose)		
		accel_tbl = wx.AcceleratorTable([
			(wx.ACCEL_CTRL,  ord('S'), randomId ),
			(wx.ACCEL_CTRL,  ord('Q'), randomId ),
			(wx.ACCEL_CTRL, ord('H'), helpItem.GetId()),
			(wx.ACCEL_CTRL,  ord('F'), findItem.GetId(),
			(wx.ACCEL_NORMAL, wx.WXK_F3, findNextItem.GetId()) )])
		
		#self.SetAcceleratorTable(accel_tbl)
		
		#accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL,  ord('Q'), randomId )])
		self.SetAcceleratorTable(accel_tbl)	
	def OnOpenShellWindow(self, evt):
		if self.shell:
			# if it already exists then just make sure it's visible
			s = self.shell
			if s.IsIconized():
				s.Iconize(False)
			s.Raise()
		else:
			# Make a PyShell window
			from wx import py
			namespace = { 'wx'    : wx,
						  'app'   : wx.GetApp(),
						  'frame' : self,
						  }
			self.shell = py.shell.ShellFrame(None, locals=namespace)
			self.shell.SetSize((640,480))
			self.shell.Show()

			# Hook the close event of the main frame window so that we
			# close the shell at the same time if it still exists            
			def CloseShell(evt):
				if self.shell:
					self.shell.Close()
				evt.Skip()
			self.Bind(wx.EVT_CLOSE, CloseShell)		
	def OnOpenWidgetInspector(self, evt):
		# Activate the widget inspection tool
		from wx.lib.inspection import InspectionTool
		if not InspectionTool().initialized:
			InspectionTool().Init()

		# Find a widget to be selected in the tree.  Use either the
		# one under the cursor, if any, or this frame.
		wnd = wx.FindWindowAtPointer()
		if not wnd:
			wnd = self
		InspectionTool().Show(wnd, True)			
	def OnDemoMenu(self, event):
		try:
			selectedDemo = self.treeMap[self.mainmenu.GetLabel(event.GetId())]
		except:
			selectedDemo = None
		if selectedDemo:
			self.tree.SelectItem(selectedDemo)
			self.tree.EnsureVisible(selectedDemo)
	def OnToggleRedirect(self, event):
		app = wx.GetApp()
		if event.Checked():
			app.RedirectStdio()
			print "Print statements and other standard output will now be directed to this window."
		else:
			app.RestoreStdio()
			print "Print statements and other standard output will now be sent to the usual location."		
	def OnFileExit(self, *event):
		self.Close()
	def OnFind(self, event):
		selected_num = self.panel.nb.GetSelection()            
		selected = self.panel.nb.GetPage(selected_num)
		editor = selected.qp.editor
		#self.nb.SetSelection(1)
		end = editor.GetLastPosition()
		textstring = editor.GetRange(0, end).lower()
		findstring = self.finddata.GetFindString().lower()
		print '>>',findstring
		#sys.exit(1)
		backward = not (self.finddata.GetFlags() & wx.FR_DOWN)
		if backward:
			start = editor.GetSelection()[0]
			loc = textstring.rfind(findstring, 0, start)
		else:
			start = editor.GetSelection()[1]
			loc = textstring.find(findstring, start)
		if loc == -1 and start != 0:
			# string not found, start at beginning
			if backward:
				start = end
				loc = textstring.rfind(findstring, 0, start)
			else:
				start = 0
				loc = textstring.find(findstring, start)
		if loc == -1:
			dlg = wx.MessageDialog(self, 'Find String Not Found',
						  'Find String Not Found in Demo File',
						  wx.OK | wx.ICON_INFORMATION)
			dlg.ShowModal()
			dlg.Destroy()
		if self.finddlg:
			if loc == -1:
				self.finddlg.SetFocus()
				return
			else:
				self.finddlg.Destroy()
				self.finddlg = None
		editor.ShowPosition(loc)
		editor.SetSelection(loc, loc + len(findstring))



	def OnFindNext(self, event):
		print 'OnFindNext, ',self.finddata
		if self.finddata.GetFindString():
			self.OnFind(event)
		else:
			self.OnHelpFind(event)

	def OnFindClose(self, event):
		event.GetDialog().Destroy()
		self.finddlg = None
	def OnHelpAbout(self, event):
		from About import MyAboutBox
		about = MyAboutBox(self)
		about.ShowModal()
		about.Destroy()

	def OnHelpFind(self, event):
		print 'OnHelpFind, ', self.finddlg
		if self.finddlg != None:
			return		
		#self.nb.SetSelection(1)
		#self.finddata='test'
		selected_num = self.panel.nb.GetSelection()            
		selected = self.panel.nb.GetPage(selected_num)
		editor = selected.qp.editor

		start, end = editor.GetSelection()
		print '\nSelection:-------', start, end
		text = editor.GetText()
		#if wx.Platform == "__WXMSW__":  # This is why GetStringSelection was added
		#	text = text.replace('\n', '\r\n')		
		selected=text[start:end]
		print selected
		self.finddata.SetFindString(selected)
		self.finddlg = wx.FindReplaceDialog(self, self.finddata, "Find",
						wx.FR_NOMATCHCASE | wx.FR_NOWHOLEWORD)
		
		self.finddlg.Show(True)
		#print(dir(self.finddlg))
		
	def onKeyCombo(self, event):
		""""""
		print "You pressed CTRL+Q!"

	def OnExit(self, event):
		self.Close(True)
		
	def on_new(self, event):
		print "on new"
		self.panel.AddNew(None)
		#self.new =self.new+1
		
	def OnOpen(self,e):
		""" Open a file"""
		self.dirname = ''
		dlg = wx.FileDialog(self, "Choose a file", self.dirname, "", "*.*", wx.OPEN)
		if dlg.ShowModal() == wx.ID_OK:
			self.filename = dlg.GetFilename()
			self.dirname = dlg.GetDirectory()
			f = open(os.path.join(self.dirname, self.filename), 'r')

			self.panel.AddNew(self.filename,f.read(), True)	
			selected_num = self.panel.nb.GetSelection()            
			selected = self.panel.nb.GetPage(selected_num)
			print  'after AddNew' , selected.qp.editor.ignore_change
			selected.qp.editor.ignore_change=True
			print selected_num
			#self.panel.nb.SetPageText(selected_num,self.filename)	
			#print dir(tab.qp.page)			
			#tab.qp.page.SetValue()
			

			f.close()
		dlg.Destroy()
		selected_num = self.panel.nb.GetSelection()            
		selected = self.panel.nb.GetPage(selected_num)
		#selected.UnChange()
		#selected.NoticeChange()
		selected.UnChange()
		print  'end 2' , selected.qp.editor.ignore_change
		print  'selected.Id ' , selected.Id
		#tab.SetFocus()
		#selected_page = self.help_notebook.GetPage(selected_page_number)	
		#self.panel.nb.SetPageText(selected_num,'test')		

	def OnSave(self,e):
		""" Save file"""
		print 'in OnSave'
		selected_num = self.panel.nb.GetSelection()            
		selected = self.panel.nb.GetPage(selected_num)
		value =selected.qp.page.GetText()
		print selected.file_name
		if not selected.saved:
			self.dirname = ''
			dlg = wx.FileDialog(self, "Save file", self.dirname, selected.file_name, "*.sql", wx.SAVE)
			if dlg.ShowModal() == wx.ID_OK:
			
				#selected.file_name = dlg.GetFilename()
				#print  self.filename
				selected.dirname = dlg.GetDirectory()
				selected.file_name=os.path.join(self.dirname, dlg.GetFilename())
				selected.saved=True
			dlg.Destroy()
			#print  self.dirname
		f = open(selected.file_name, 'w')
			#self.panel.AddNew(self.filename,f.read())	
			#print dir(tab.qp.page)			
			#tab.qp.page.SetValue()
			#print 'value: ', value
		f.write(value)
		f.close()
		print 'selected_num= ',selected_num
		#print 'self.filename= ', self.filename
		self.panel.nb.SetPageText(selected_num,selected.file_name)
		selected.UnChange()
		
	def OnSaveAs(self,e):
		""" SaveAs file"""
		selected_num = self.panel.nb.GetSelection()            
		selected = self.panel.nb.GetPage(selected_num)
		value =selected.qp.page.GetText()
		#print selected.file_name
		self.dirname = ''
		dlg = wx.FileDialog(self, "Save file As", self.dirname, selected.file_name, "*.sql", wx.SAVE)
		if dlg.ShowModal() == wx.ID_OK:
			
			#self.filename = dlg.GetFilename()
			#print  self.filename
			selected.dirname = dlg.GetDirectory()
			selected.file_name=os.path.join(self.dirname, dlg.GetFilename())
			selected.saved=True
			#print  self.dirname
			f = open(selected.file_name, 'w')
				#self.panel.AddNew(self.filename,f.read())	
				#print dir(tab.qp.page)			
				#tab.qp.page.SetValue()
				#print 'value: ', value
			f.write(value)
			f.close()	
			#print self.filename
			self.panel.nb.SetPageText(selected_num,selected.file_name)
			selected.UnChange()			
		dlg.Destroy()

		#pass	
		
	def OnAbout(self,e):
		# Create a message dialog box
		dlg = wx.MessageDialog(self, "NZ SQL", "About Netezza SQL Editor", wx.OK)
		dlg.ShowModal() # Shows it
		dlg.Destroy() # finally destroy it when finished.
		
#----------------------------------------------------------------------
import wx.lib.agw.pybusyinfo as PBI

#----------------------------------------------------------------------
def ShowMessage(msg, icon):
	dlg = wx.MessageDialog(None, msg, 'Notification', icon
						   #wx.YES_NO | wx.NO_DEFAULT | wx.CANCEL | wx.ICON_INFORMATION
						   )
	dlg.ShowModal()
	dlg.Destroy()

def showmsg():
	app = wx.App(redirect=False)
	msg = 'this is a test'
	title = 'Message!'
	d = PBI.PyBusyInfo(msg, title=title)
	return d 
	
	
if __name__ == "__main__":
	"""
	d = showmsg()
	time.sleep(3)
	d = None
	sys.exit(0)
	"""
	import sys
	from wx.lib.mixins.inspection import InspectableApp
	app = InspectableApp(False)
	frame = Main(None, sys.stdout)
	frame.Show(True)
	#import wx.lib.inspection
	#wx.lib.inspection.InspectionTool().Show()
	app.MainLoop()	